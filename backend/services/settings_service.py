"""应用设置服务 —— BYOK：用户自备 API Key，存本地 DB（环境变量作出厂默认）

读取优先级：app_settings(DB 用户设置) → config 环境变量（.env）→ 内置默认。
scope 字段预留给多用户升级（当前恒 'global'，将来放 user_id 无需改表）。
Key 以明文存本地 SQLite（与 .env 同级，本地单用户定位，文档已披露）。
"""

from config import (
    AI_API_KEY,
    AI_BASE_URL,
    AI_EMBEDDING_API_KEY,
    AI_EMBEDDING_BASE_URL,
    AI_EMBEDDING_MODEL,
    AI_MODEL,
    AI_PROVIDER,
)

SCOPE_GLOBAL = "global"

# 可设置项及其环境变量回退（出厂默认）
_FIELDS = {
    "ai_provider": AI_PROVIDER,
    "ai_api_key": AI_API_KEY,
    "ai_base_url": AI_BASE_URL,
    "ai_model": AI_MODEL,
    "ai_embedding_base_url": AI_EMBEDDING_BASE_URL,
    "ai_embedding_api_key": AI_EMBEDDING_API_KEY,
    "ai_embedding_model": AI_EMBEDDING_MODEL,
}

ALLOWED_KEYS = set(_FIELDS)


class SettingsService:
    """设置读写：DB 覆盖环境变量默认"""

    @staticmethod
    async def get_all(scope: str = SCOPE_GLOBAL) -> dict:
        """合并后的生效配置（DB 覆盖 env 出厂默认）"""
        from database import get_db
        db = await get_db()
        rows = await db.execute_fetchall(
            "SELECT key, value FROM app_settings WHERE scope = ?", [scope])
        overrides = {r["key"]: r["value"] for r in rows if r["key"] in ALLOWED_KEYS}
        merged = dict(_FIELDS)
        merged.update(overrides)
        return merged

    @staticmethod
    async def update(values: dict, scope: str = SCOPE_GLOBAL) -> int:
        """写入设置。

        非法 key 抛 ValueError；value 为 None 或空串 → 删除该项覆盖（回退出厂默认）。
        """
        from datetime import datetime

        from database import get_db

        unknown = set(values) - ALLOWED_KEYS
        if unknown:
            raise ValueError(f"不支持的设置项: {', '.join(sorted(unknown))}")

        db = await get_db()
        now = datetime.now().isoformat()
        for key, value in values.items():
            if value is None or str(value).strip() == "":
                await db.execute(
                    "DELETE FROM app_settings WHERE scope = ? AND key = ?", [scope, key])
            else:
                await db.execute(
                    "INSERT INTO app_settings (scope, key, value, updated_at) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(scope, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    [scope, key, str(value), now])
        await db.commit()
        return len(values)
