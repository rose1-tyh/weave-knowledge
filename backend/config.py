"""应用配置"""

import os

from dotenv import load_dotenv

load_dotenv()

# 应用版本（main.py 元信息 / /api/health / 桌面启动器共用）
APP_VERSION = "3.3.0"

# AI 提供方: 'anthropic'（Claude）或 'openai'（DeepSeek 等 OpenAI 兼容接口）
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
AI_API_KEY = os.getenv("AI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL = os.getenv(
    "AI_MODEL",
    "claude-sonnet-4-20250514" if AI_PROVIDER == "anthropic" else "deepseek-chat",
)
# OpenAI 兼容接口 base url（DeepSeek / vLLM / OneAPI 等）
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com")

# 可插拔 embedding（概念语义对齐精排；DeepSeek/Anthropic 无 embedding API，
# 留空则回退纯字符相似度。可配硅基流动等 OpenAI 兼容 /embeddings 提供方）
AI_EMBEDDING_BASE_URL = os.getenv("AI_EMBEDDING_BASE_URL", "")
AI_EMBEDDING_API_KEY = os.getenv("AI_EMBEDDING_API_KEY", "")
AI_EMBEDDING_MODEL = os.getenv("AI_EMBEDDING_MODEL", "text-embedding-3-small")

# 数据目录：WEAVE_DATA_DIR 环境变量优先（打包启动器设为 %APPDATA%\织识）；
# 未设置时保持项目内 backend/storage（开发模式与存量数据不受影响）
WEAVE_DATA_DIR = os.getenv("WEAVE_DATA_DIR", "").strip()
_data_root = WEAVE_DATA_DIR if WEAVE_DATA_DIR else os.path.join(os.path.dirname(__file__), "storage")

# 论文存储
PAPER_STORAGE_DIR = os.path.join(_data_root, "papers")
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}

# 文本处理
MAX_CHUNK_CHARS = 80000

# 数据库
DATABASE_PATH = os.path.join(_data_root, "weave.db")
