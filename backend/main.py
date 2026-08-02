"""「织识」— 学术知识重构引擎 后端入口"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload, knowledge
from database import init_db, close_db
from config import PAPER_STORAGE_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(PAPER_STORAGE_DIR, exist_ok=True)
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="织识 API v2.0",
    description="学术知识重构引擎 —— 知识库管理 + AI 提取 + 知识编辑 + 跨论文融合",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(knowledge.router)


@app.get("/")
def root():
    return {"name": "织识 API", "version": "2.0.0"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
