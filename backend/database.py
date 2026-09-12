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

        -- 提取任务持久化：每篇论文保留最新一次任务的阶段/进度/错误（可跨重启查询、可重试）
        CREATE TABLE IF NOT EXISTS extract_tasks (
            paper_id TEXT PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
            stage TEXT DEFAULT 'queued',
            progress REAL DEFAULT 0,
            detail TEXT DEFAULT '',
            message TEXT DEFAULT '',
            error TEXT DEFAULT '',
            updated_at TEXT NOT NULL
        );

        -- 概念全文索引（FTS5 trigram：支持中文子串匹配；<3 字符查询回退 LIKE）
        CREATE VIRTUAL TABLE IF NOT EXISTS concepts_fts USING fts5(
            name, definition,
            content='concepts', content_rowid='id',
            tokenize='trigram'
        );

        CREATE TRIGGER IF NOT EXISTS concepts_ai AFTER INSERT ON concepts BEGIN
            INSERT INTO concepts_fts(rowid, name, definition) VALUES (new.id, new.name, new.definition);
        END;
        CREATE TRIGGER IF NOT EXISTS concepts_ad AFTER DELETE ON concepts BEGIN
            INSERT INTO concepts_fts(concepts_fts, rowid, name, definition)
            VALUES ('delete', old.id, old.name, old.definition);
        END;
        CREATE TRIGGER IF NOT EXISTS concepts_au AFTER UPDATE ON concepts BEGIN
            INSERT INTO concepts_fts(concepts_fts, rowid, name, definition)
            VALUES ('delete', old.id, old.name, old.definition);
            INSERT INTO concepts_fts(rowid, name, definition) VALUES (new.id, new.name, new.definition);
        END;

        -- 启动时重建全文索引（幂等；覆盖存量数据与旧库升级路径）
        INSERT INTO concepts_fts(concepts_fts) VALUES('rebuild');
    """)
    await migrate_schema(db)
    await db.commit()


# 幂等迁移：表名 → 需补充的列定义（SQLite 无 IF NOT EXISTS for ADD COLUMN）
MIGRATIONS = {
    "papers": ["text TEXT DEFAULT ''"],
    "concepts": [
        "evidence TEXT DEFAULT ''",
        "confidence REAL DEFAULT 0.5",
        "confidence_ai REAL",
        "status TEXT DEFAULT 'pending'",
    ],
    "relations": [
        "confidence REAL DEFAULT 0.5",
        "confidence_ai REAL",
        "status TEXT DEFAULT 'pending'",
        "page INTEGER",
    ],
}


async def migrate_schema(db):
    """幂等迁移：对缺失列执行 ALTER TABLE ADD COLUMN"""
    for table, columns in MIGRATIONS.items():
        rows = await db.execute_fetchall(f"PRAGMA table_info({table})")
        existing = {r["name"] for r in rows}
        for col in columns:
            col_name = col.split(" ")[0]
            if col_name not in existing:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
    await db.commit()


async def close_db():
    """关闭数据库连接"""
    global DB
    if DB:
        await DB.close()
        DB = None
