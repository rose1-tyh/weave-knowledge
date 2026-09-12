import aiosqlite
import database
import pytest


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
