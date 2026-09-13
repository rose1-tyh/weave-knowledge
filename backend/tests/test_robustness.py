"""健壮性与安全加固测试 —— SSRF 防护 / 请求 ID 中间件 / 404 语义 / Pydantic 校验"""
import pytest
from fastapi import HTTPException
from routers.extract import _validate_public_url
from services.library_service import LibraryService


def _allow(host):
    import socket
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, 0))]


def test_ssrf_blocks_private_and_loopback(monkeypatch):
    """私网/环回/链路本地地址一律拒绝"""
    import socket

    def fake_getaddrinfo(host, port):
        return _allow(host)

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    for url in (
        "http://127.0.0.1/x", "http://10.0.0.5/x", "http://192.168.1.1/x",
        "http://172.16.0.9/x", "http://169.254.169.254/latest/meta-data",
        "ftp://example.com/x", "file:///etc/passwd",
    ):
        with pytest.raises(HTTPException):
            _validate_public_url(url)


def test_ssrf_allows_public_http(monkeypatch):
    """公网 http/https 放行"""
    import socket
    monkeypatch.setattr(socket, "getaddrinfo", lambda h, p: _allow("93.184.216.34"))
    assert _validate_public_url("https://example.com/paper") == "https://example.com/paper"


def test_ssrf_rejects_unresolvable_host(monkeypatch):
    import socket

    def boom(h, p):
        raise socket.gaierror("no dns")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    with pytest.raises(HTTPException) as ei:
        _validate_public_url("https://nonexistent.invalid/x")
    assert "解析" in ei.value.detail


async def test_delete_missing_concept_returns_404(db):
    """删除不存在的概念 → 404（此前静默 200）"""
    from routers.graph import delete_concept, delete_relation
    with pytest.raises(HTTPException) as ei:
        await delete_concept("p-missing", "abc12345")
    assert ei.value.status_code == 404
    with pytest.raises(HTTPException) as ei:
        await delete_relation("p-missing", 999)
    assert ei.value.status_code == 404


async def test_delete_missing_paper_returns_404(db):
    from routers.library import delete_paper
    with pytest.raises(HTTPException) as ei:
        await delete_paper("p-missing")
    assert ei.value.status_code == 404


async def test_patch_paper_uses_pydantic_and_404(db):
    """PATCH 论文：Pydantic 白名单字段 + 不存在返回 404"""
    from models.schemas import PaperUpdate
    from routers.library import update_paper

    with pytest.raises(HTTPException) as ei:
        await update_paper("p-missing", PaperUpdate(title="新标题"))
    assert ei.value.status_code == 404

    await db.execute(
        "INSERT INTO papers (id, title, filename, upload_time) "
        "VALUES ('p1', '旧标题', 'a.pdf', '2026-09-01')")
    await db.commit()
    await update_paper("p1", PaperUpdate(title="新标题", notes="备注"))
    paper = await LibraryService.get_paper("p1")
    assert paper["title"] == "新标题"
    assert paper["notes"] == "备注"


async def test_create_relation_requires_existing_concepts(db):
    """创建关系：两端概念不存在 → 400"""
    from models.schemas import RelationCreate
    from routers.graph import create_relation

    await db.execute(
        "INSERT INTO papers (id, title, filename, upload_time) "
        "VALUES ('p1', 't', 'a.pdf', '2026-09-01')")
    await db.commit()
    with pytest.raises(HTTPException) as ei:
        await create_relation("p1", RelationCreate(source_slug="ghost1", target_slug="ghost2"))
    assert ei.value.status_code == 400


def test_request_id_middleware_sets_header_and_logging(monkeypatch):
    """中间件：响应携带 X-Request-ID（透传外部 ID），访问日志带 rid"""
    import logging

    from logging_setup import RequestIDMiddleware, setup_logging

    monkeypatch.setattr("logging_setup._configured", False)
    setup_logging()

    records = []
    capture = logging.Handler()
    capture.emit = lambda record: records.append(record)
    logging.getLogger("weave.access").addHandler(capture)

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    with TestClient(app) as client:
        resp = client.get("/ping")
        assert resp.headers.get("x-request-id")
        resp2 = client.get("/ping", headers={"X-Request-ID": "test-rid-42"})
        assert resp2.headers["x-request-id"] == "test-rid-42"

    assert any("test-rid-42" in r.getMessage() for r in records)
    logging.getLogger("weave.access").removeHandler(capture)


def test_health_reports_version_and_app_mode(monkeypatch):
    """/api/health：版本号 + 桌面应用模式标记（run.py 设 WEAVE_APP_MODE）"""
    from main import health

    monkeypatch.delenv("WEAVE_APP_MODE", raising=False)
    payload = health()
    assert payload["status"] == "ok"
    assert payload["version"]
    assert payload["appMode"] is False

    monkeypatch.setenv("WEAVE_APP_MODE", "1")
    assert health()["appMode"] is True
