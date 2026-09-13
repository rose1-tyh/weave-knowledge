"""日志基础设施 —— weave 根 logger（滚动文件）+ 请求 ID 中间件

- 日志文件位于数据目录（WEAVE_DATA_DIR 或 backend/storage），2MB×3 滚动；
- 每个请求生成/透传 X-Request-ID，访问日志与异常堆栈均携带，便于串联排查；
- setup_logging 幂等（TestClient 多次触发 lifespan 不会重复挂 handler）。
"""

import logging
import logging.handlers
import os
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

_configured = False


def setup_logging() -> logging.Logger:
    """初始化 weave 日志（幂等）：滚动文件 + 控制台"""
    global _configured
    logger = logging.getLogger("weave")
    if _configured:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s [%(name)s] %(message)s")

    from config import DATABASE_PATH
    log_path = os.path.join(os.path.dirname(DATABASE_PATH), "weave.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)  # 数据目录可能尚不存在（CI/首次运行）
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    _configured = True
    return logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件：X-Request-ID 透传 + 结构化访问日志 + 未处理异常落盘"""

    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("weave.access")

    async def dispatch(self, request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self.logger.exception("%s %s rid=%s — 未处理异常",
                                  request.method, request.url.path, rid)
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        self.logger.info("%s %s → %s %.0fms rid=%s",
                         request.method, request.url.path,
                         response.status_code, elapsed_ms, rid)
        return response
