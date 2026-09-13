"""应用设置接口 —— BYOK 自带 API Key（读取掩码回显，写入校验，连通性测试）"""

from fastapi import APIRouter, HTTPException
from models.schemas import R, SettingsTestRequest, SettingsUpdate
from services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])

_MASK_MARK = "****"


def _mask_key(key: str) -> str:
    """Key 掩码回显：保留前 3 后 4（短 Key 全遮），防偷窥"""
    if not key:
        return ""
    if len(key) <= 8:
        return _MASK_MARK
    return f"{key[:3]}{_MASK_MARK}{key[-4:]}"


async def _settings_view() -> dict:
    s = await SettingsService.get_all()
    return {
        "aiProvider": s["ai_provider"],
        "apiKeyMasked": _mask_key(s["ai_api_key"]),
        "hasKey": bool(s["ai_api_key"]),
        "aiBaseUrl": s["ai_base_url"],
        "aiModel": s["ai_model"],
        "embeddingBaseUrl": s["ai_embedding_base_url"],
        "embeddingApiKeyMasked": _mask_key(s["ai_embedding_api_key"]),
        "hasEmbedding": bool(s["ai_embedding_base_url"] and s["ai_embedding_api_key"]),
        "embeddingModel": s["ai_embedding_model"],
    }


@router.get("")
async def get_settings():
    """当前生效配置（API Key 仅掩码回显，不返回原文）"""
    return R.success(data=await _settings_view())


@router.put("")
async def update_settings(req: SettingsUpdate):
    """写入设置。

    - API Key 为空串 → 清除该项覆盖（回退出厂默认）；含掩码标记 → 视为未修改忽略
    - base_url 需以 http(s) 开头
    """
    values = {}
    for field in ("ai_provider", "ai_base_url", "ai_model",
                  "ai_embedding_base_url", "ai_embedding_api_key", "ai_embedding_model"):
        val = getattr(req, field)
        if val is not None:
            values[field] = val.strip() if isinstance(val, str) else val

    key_val = req.ai_api_key
    if key_val is not None and _MASK_MARK not in key_val:
        values["ai_api_key"] = key_val.strip()

    for url_field in ("ai_base_url", "ai_embedding_base_url"):
        url = values.get(url_field)
        if url and not url.startswith(("http://", "https://")):
            raise HTTPException(400, detail=f"{url_field} 必须以 http:// 或 https:// 开头")

    try:
        await SettingsService.update(values)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    return R.success(data=await _settings_view(), msg="设置已保存")


@router.post("/test")
async def test_settings(req: SettingsTestRequest):
    """连通性测试：用提交的（未提供字段回退已保存）配置发一次最小请求。

    不落库——先测后存。无 Key 时返回 ok=False 而非报错（前端展示引导文案）。
    """
    from services.ai_service import AIService

    merged = await SettingsService.get_all()
    overrides = {
        "ai_provider": req.ai_provider if req.ai_provider is not None else merged["ai_provider"],
        "ai_api_key": (req.ai_api_key if (req.ai_api_key is not None and _MASK_MARK not in req.ai_api_key)
                       else merged["ai_api_key"]),
        "ai_base_url": req.ai_base_url if req.ai_base_url is not None else merged["ai_base_url"],
        "ai_model": req.ai_model if req.ai_model is not None else merged["ai_model"],
    }
    if not overrides["ai_api_key"]:
        return R.success(data={"ok": False, "error": "未配置 API Key，请先填写并保存"})

    import asyncio
    result = await asyncio.to_thread(
        AIService.probe,
        provider=overrides["ai_provider"],
        api_key=overrides["ai_api_key"],
        base_url=overrides["ai_base_url"],
        model=overrides["ai_model"],
    )
    return R.success(data=result)
