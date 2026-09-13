import aiosqlite
import database
import pytest


@pytest.fixture
async def seeded_ai_key(db):
    """注入测试 API Key：让提取类测试与开发机 .env 解耦（CI 无 .env 也能跑）"""
    from datetime import datetime
    await db.execute(
        "INSERT OR REPLACE INTO app_settings (scope, key, value, updated_at) "
        "VALUES ('global', 'ai_api_key', 'sk-test-key', ?)",
        [datetime.now().isoformat()])
    await db.commit()


@pytest.fixture
async def db(tmp_path):
    """临时 SQLite 连接，跑 init_db 建表；测试间隔离"""
    conn = await aiosqlite.connect(tmp_path / "test.db")
    conn.row_factory = aiosqlite.Row
    # 与 database.get_db 保持一致（外键级联依赖此 PRAGMA）
    await conn.execute("PRAGMA foreign_keys=ON")
    database.DB = conn
    await database.init_db()
    yield conn
    await conn.close()
    database.DB = None
