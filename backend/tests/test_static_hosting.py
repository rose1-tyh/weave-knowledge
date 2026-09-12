"""静态托管测试 —— 后端托管前端构建产物 + SPA fallback（Vue history 路由）"""
import os

import pytest
from fastapi.testclient import TestClient

# 前置条件：前端构建产物存在（npm run build 产出 frontend/dist）
DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")


@pytest.fixture(scope="module")
def client():
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.mark.skipif(not os.path.isdir(DIST_DIR), reason="frontend/dist 不存在，先执行 npm run build")
def test_root_serves_index_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "织识" in resp.text or "<div id=" in resp.text


@pytest.mark.skipif(not os.path.isdir(DIST_DIR), reason="frontend/dist 不存在，先执行 npm run build")
def test_api_health_still_works(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.skipif(not os.path.isdir(DIST_DIR), reason="frontend/dist 不存在，先执行 npm run build")
def test_spa_fallback_for_history_routes(client):
    """Vue Router history 模式：未知前端路由返回 index.html 而非 404"""
    for path in ["/library", "/workbench/abc123", "/explore"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} 应返回 index.html"
        assert "text/html" in resp.headers["content-type"]
