import aiosqlite
import pytest
import database


@pytest.fixture
async def db(tmp_path):
    """临时 SQLite 连接，跑 init_db 建表；测试间隔离"""
    conn = await aiosqlite.connect(tmp_path / "test.db")
    conn.row_factory = aiosqlite.Row
    database.DB = conn
    await database.init_db()
    yield conn
    await conn.close()
    database.DB = None
