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

        -- 应用设置（BYOK 自带 API Key）：scope 预留多用户升级位（当前恒 'global'）
        CREATE TABLE IF NOT EXISTS app_settings (
            scope TEXT NOT NULL DEFAULT 'global',
            key TEXT NOT NULL,
            value TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (scope, key)
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

        -- 论文正文全文索引（标题 + 正文，全文检索通道的数据源）
        CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
            title, text,
            content='papers', content_rowid='rowid',
            tokenize='trigram'
        );

        CREATE TRIGGER IF NOT EXISTS papers_fts_ai AFTER INSERT ON papers BEGIN
            INSERT INTO papers_fts(rowid, title, text) VALUES (new.rowid, new.title, new.text);
        END;
        CREATE TRIGGER IF NOT EXISTS papers_fts_ad AFTER DELETE ON papers BEGIN
            INSERT INTO papers_fts(papers_fts, rowid, title, text)
            VALUES ('delete', old.rowid, old.title, old.text);
        END;
        CREATE TRIGGER IF NOT EXISTS papers_fts_au AFTER UPDATE ON papers BEGIN
            INSERT INTO papers_fts(papers_fts, rowid, title, text)
            VALUES ('delete', old.rowid, old.title, old.text);
            INSERT INTO papers_fts(rowid, title, text) VALUES (new.rowid, new.title, new.text);
        END;

        -- 概念语义向量（混合检索语义通道；未配置 embedding 时为空表，检索自动降级）
        CREATE TABLE IF NOT EXISTS concept_embeddings (
            paper_id TEXT NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            slug TEXT NOT NULL,
            model TEXT NOT NULL,
            dim INTEGER NOT NULL,
            vector BLOB NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (paper_id, slug, model)
        );
    """)
    await migrate_schema(db)
    await _rebuild_fts_if_stale(db)
    await db.commit()


async def _rebuild_fts_if_stale(db):
    """按需重建全文索引：仅当 FTS 行数与主表不一致（首建/存量迁移/失同步）时执行，
    避免启动时无条件全量 rebuild 随库增长变慢"""
    for fts_table, main_table in (("concepts_fts", "concepts"), ("papers_fts", "papers")):
        fts_cnt = (await db.execute_fetchall(f"SELECT COUNT(*) AS c FROM {fts_table}"))[0]["c"]
        main_cnt = (await db.execute_fetchall(f"SELECT COUNT(*) AS c FROM {main_table}"))[0]["c"]
        if fts_cnt != main_cnt:
            await db.execute(f"INSERT INTO {fts_table}(fts_table) VALUES('rebuild')")


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
