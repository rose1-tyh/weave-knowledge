"""BYOK 设置系统测试 —— 读写回退链 / 掩码 / 校验 / 连通性探测 / 动态生效"""
import pytest
from fastapi import HTTPException
from services.ai_service import AIService
from services.settings_service import SettingsService


@pytest.fixture
def factory_defaults(monkeypatch):
    """固定出厂默认（隔离真实 .env），返回可变字典供用例改写"""
    defaults = {
        "ai_provider": "openai", "ai_api_key": "sk-env-default", "ai_base_url": "https://api.example.com",
        "ai_model": "env-model", "ai_embedding_base_url": "", "ai_embedding_api_key": "",
        "ai_embedding_model": "text-embedding-3-small",
    }
    import services.settings_service as ss
    monkeypatch.setattr(ss, "_FIELDS", dict(defaults))
    monkeypatch.setattr(ss, "ALLOWED_KEYS", set(defaults))
    return defaults


async def test_defaults_fall_back_when_db_empty(db, factory_defaults):
    """无 DB 覆盖 → 回退出厂默认（env）"""
    merged = await SettingsService.get_all()
    assert merged["ai_api_key"] == "sk-env-default"
    assert merged["ai_model"] == "env-model"


async def test_update_overrides_and_clear_restores(db, factory_defaults):
    """DB 覆盖生效；空值清除覆盖后回退默认"""
    await SettingsService.update({"ai_api_key": "sk-user-key", "ai_model": "glm-4.6"})
    merged = await SettingsService.get_all()
    assert merged["ai_api_key"] == "sk-user-key"
    assert merged["ai_model"] == "glm-4.6"
    # 未覆盖的项保持默认
    assert merged["ai_base_url"] == "https://api.example.com"

    # 空串清除 → 回退
    await SettingsService.update({"ai_model": ""})
    assert (await SettingsService.get_all())["ai_model"] == "env-model"


async def test_update_rejects_unknown_keys(db):
    with pytest.raises(ValueError):
        await SettingsService.update({"hacker_key": "x"})


async def test_for_settings_builds_client(db, factory_defaults):
    """AIService.for_settings：从合并配置构造实例"""
    await SettingsService.update({"ai_provider": "openai", "ai_api_key": "sk-zhipu",
                                  "ai_base_url": "https://open.bigmodel.cn/api/paas/v4",
                                  "ai_model": "glm-4.6"})
    svc = AIService.for_settings(await SettingsService.get_all())
    assert svc.provider == "openai"
    assert svc.api_key == "sk-zhipu"
    assert svc.base_url == "https://open.bigmodel.cn/api/paas/v4"
    assert svc.model == "glm-4.6"


def test_anthropic_client_lazy_and_cached():
    """anthropic SDK 客户端延迟创建且按实例缓存"""
    svc = AIService(provider="anthropic", api_key="sk-ant-test")
    assert svc._anthropic is None  # 构造时不建连接
    client = svc._anthropic_client()
    assert client is svc._anthropic_client()  # 缓存


# ── 路由层 ──

async def test_get_settings_masks_key(db, factory_defaults):
    """GET 掩码回显：hasKey + 星号，不泄露原文"""
    await SettingsService.update({"ai_api_key": "sk-abcdef1234567890"})
    from routers.settings import _mask_key, get_settings
    data = (await get_settings()).data
    assert data["hasKey"] is True
    assert "****" in data["apiKeyMasked"]
    assert "sk-abcdef1234567890" not in str(data)
    assert data["aiModel"] == "env-model"
    assert _mask_key("short") == "****"


async def test_put_settings_ignores_masked_and_validates(db, factory_defaults):
    """PUT：掩码值视为未修改；非法 base_url 400"""
    from models.schemas import SettingsUpdate
    from routers.settings import update_settings

    await SettingsService.update({"ai_api_key": "sk-real-key"})

    # 掩码回传 → 不覆盖；同时更新 model
    await update_settings(SettingsUpdate(ai_api_key="sk-****8900", ai_model="deepseek-chat"))
    merged = await SettingsService.get_all()
    assert merged["ai_api_key"] == "sk-real-key"
    assert merged["ai_model"] == "deepseek-chat"

    # 非法 base_url
    with pytest.raises(HTTPException) as ei:
        await update_settings(SettingsUpdate(ai_base_url="ftp://x"))
    assert ei.value.status_code == 400


async def test_put_settings_clears_key_with_empty_string(db, factory_defaults):
    """Key 传空串 → 清除用户覆盖，回退 env 默认"""
    from models.schemas import SettingsUpdate
    from routers.settings import update_settings

    await SettingsService.update({"ai_api_key": "sk-user"})
    await update_settings(SettingsUpdate(ai_api_key=""))
    assert (await SettingsService.get_all())["ai_api_key"] == "sk-env-default"


async def test_test_endpoint_no_key(db, monkeypatch):
    """无 Key → ok=False 引导文案（不抛错）"""
    import services.settings_service as ss
    monkeypatch.setattr(ss, "_FIELDS", {k: "" for k in ss._FIELDS})
    from models.schemas import SettingsTestRequest
    from routers.settings import test_settings
    result = (await test_settings(SettingsTestRequest())).data
    assert result["ok"] is False
    assert "未配置" in result["error"]


async def test_test_endpoint_probes_with_merged_config(db, factory_defaults, monkeypatch):
    """test 端点：提交字段覆盖已存配置，探测成功返回延迟"""
    calls = {}

    def fake_probe(provider, api_key, base_url, model):
        calls.update(provider=provider, api_key=api_key, base_url=base_url, model=model)
        return {"ok": True, "latencyMs": 233}

    monkeypatch.setattr(AIService, "probe", staticmethod(fake_probe))
    from models.schemas import SettingsTestRequest
    from routers.settings import test_settings

    result = (await test_settings(SettingsTestRequest(ai_api_key="sk-new", ai_model="glm-4.6"))).data
    assert result["ok"] is True and result["latencyMs"] == 233
    assert calls["api_key"] == "sk-new"
    assert calls["model"] == "glm-4.6"
    assert calls["base_url"] == "https://api.example.com"  # 未提交 → 用已存默认


def test_probe_openai_shapes_request(monkeypatch):
    """probe（openai 协议）：1-token 请求打到 {base}/chat/completions"""
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, json=json, headers=headers)
        return FakeResp()

    import services.ai_service as ai
    monkeypatch.setattr(ai.requests, "post", fake_post)
    result = AIService.probe("openai", "sk-x", "https://api.deepseek.com", "deepseek-chat")
    assert result["ok"] is True
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["json"]["max_tokens"] == 1
    assert captured["headers"]["Authorization"] == "Bearer sk-x"


def test_probe_failure_returns_error(monkeypatch):
    """探测失败 → ok=False + 截断的错误信息（不抛异常）"""
    def boom(*args, **kwargs):
        raise RuntimeError("连接超时" + "x" * 500)

    import services.ai_service as ai
    monkeypatch.setattr(ai.requests, "post", boom)
    result = AIService.probe("openai", "sk-x", "https://api.example.com", "m")
    assert result["ok"] is False
    assert "连接超时" in result["error"]
    assert len(result["error"]) <= 300


async def test_extraction_uses_current_settings(db, factory_defaults, monkeypatch):
    """提取任务每次读当前设置（改 Key 立即生效）"""
    await SettingsService.update({"ai_api_key": "sk-live-key", "ai_provider": "openai"})
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
        "VALUES ('p-set', 't', 't.pdf', 1, 0, '2026-09-01', 'pending', '正文')")
    await db.commit()

    captured = {}

    async def fake_extract(self, text, title, on_progress=None):
        captured["api_key"] = self.api_key
        captured["provider"] = self.provider
        return {"concepts": [], "relations": []}

    from services import extraction_service as es
    monkeypatch.setattr(AIService, "extract_knowledge", fake_extract)
    mgr = es.ExtractionManager()
    await mgr._run("p-set")
    assert captured["api_key"] == "sk-live-key"
    assert captured["provider"] == "openai"


def test_settings_routes_registered():
    from main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/settings" in paths
    assert "/api/settings/test" in paths
