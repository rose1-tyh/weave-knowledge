"""应用配置"""

import os
from dotenv import load_dotenv

load_dotenv()

# AI 提供方: 'anthropic'（Claude）或 'openai'（DeepSeek 等 OpenAI 兼容接口）
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
AI_API_KEY = os.getenv("AI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL = os.getenv(
    "AI_MODEL",
    "claude-sonnet-4-20250514" if AI_PROVIDER == "anthropic" else "deepseek-chat",
)
# OpenAI 兼容接口 base url（DeepSeek / vLLM / OneAPI 等）
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com")

# 论文存储
PAPER_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage", "papers")
MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf"}

# 文本处理
MAX_CHUNK_CHARS = 80000

# 数据库
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "storage", "weave.db")
