"""「织识」— 学术知识重构引擎 后端入口"""

import os
import sys
from contextlib import asynccontextmanager

from config import APP_VERSION, PAPER_STORAGE_DIR
from database import close_db, init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from logging_setup import RequestIDMiddleware, setup_logging
from routers import explore, extract, graph, library, system, upload
from services.extraction_service import extraction_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    os.makedirs(PAPER_STORAGE_DIR, exist_ok=True)
    await init_db()
    # 上次进程遗留的"运行中"任务已随进程消亡，标记为失败以便前端重试
    await extraction_manager.recover_stale()
    yield
    await close_db()


app = FastAPI(
    title=f"织识 API v{APP_VERSION}",
    description="学术知识重构引擎 —— 知识库管理 + AI 提取 + 知识编辑 + 跨论文融合 + 混合检索",
    version=APP_VERSION,
    lifespan=lifespan,
)

# 本地单用户定位：仅放行 localhost 系来源（开发跨域），打包同源部署不依赖 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)

app.include_router(upload.router)
app.include_router(extract.router)
app.include_router(graph.router)
app.include_router(library.router)
app.include_router(explore.router)
app.include_router(system.router)


@app.get("/")
def root():
    # 静态托管启用时，根路径为前端页面；否则保留 API 元信息（开发模式）
    if FRONTEND_DIST:
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
    return {"name": "织识 API", "version": APP_VERSION}


@app.get("/api/health")
def health():
    # appMode：桌面启动器（run.py）设置 WEAVE_APP_MODE，前端据此启用桌面行为（记住上次页面）
    return {
        "status": "ok",
        "version": APP_VERSION,
        "appMode": os.environ.get("WEAVE_APP_MODE") == "1",
    }


# ── 前端静态托管（打包/生产模式）：API 路由之后挂载 ──
# 查找顺序：项目内 frontend/dist（开发构建）→ PyInstaller 资源目录（_MEIPASS）
_DIST_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist"),
    os.path.join(getattr(sys, "_MEIPASS", ""), "frontend", "dist"),
    os.path.join(getattr(sys, "_MEIPASS", ""), "dist"),
]
FRONTEND_DIST = next((d for d in _DIST_CANDIDATES if d and os.path.isdir(d)), None)

if FRONTEND_DIST:
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """Vue history 路由回退：真实文件返回文件，否则返回 index.html"""
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="织识后端服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
