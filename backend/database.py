"""SQLite 数据库连接管理 + 自动建表"""

import aiosqlite
from config import DATABASE_PATH

DB = None  # 全局连接引用


async def get_db():
    """获取数据库连接"""
    global DB
    if DB is None:
        DB = await aiosqlite.connect(DATABASE_PATH)
        DB.row_factory = aiosqlite.Row
        await DB.execute("PRAGMA journal_mode=WAL")
        await DB.execute("PRAGMA foreign_keys=ON")
    return DB


async def init_db():
    """初始化数据库表"""
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            filename TEXT NOT NULL,
            page_count INTEGER DEFAULT 0,
            text_length INTEGER DEFAULT 0,
            upload_time TEXT NOT NULL,
            extract_status TEXT DEFAULT 'pending',
            extract_time TEXT,
            concept_count INTEGER DEFAULT 0,
            relation_count INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]',
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            slug TEXT NOT NULL,
            name TEXT NOT NULL,
            definition TEXT DEFAULT '',
            type TEXT DEFAULT 'finding',
            page INTEGER DEFAULT 1,
            position_x REAL,
            position_y REAL,
            created_by TEXT DEFAULT 'ai',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(paper_id, slug)
        );

        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            source_slug TEXT NOT NULL,
            target_slug TEXT NOT NULL,
            type TEXT DEFAULT 'cites',
            evidence TEXT DEFAULT '',
            created_by TEXT DEFAULT 'ai',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS concept_merges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_name_a TEXT NOT NULL,
            paper_id_a TEXT NOT NULL,
            concept_name_b TEXT NOT NULL,
            paper_id_b TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            UNIQUE(concept_name_a, paper_id_a, concept_name_b, paper_id_b)
        );
    """)
    await db.commit()


async def close_db():
    """关闭数据库连接"""
    global DB
    if DB:
        await DB.close()
        DB = None
