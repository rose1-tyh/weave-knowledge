import database


async def test_migrate_schema_is_idempotent(db):
    await database.migrate_schema(db)
    await database.migrate_schema(db)  # 第二次不应报错、不重复加列

    cols = {r["name"] for r in await db.execute_fetchall("PRAGMA table_info(concepts)")}
    assert {"evidence", "confidence", "confidence_ai", "status"} <= cols

    cols = {r["name"] for r in await db.execute_fetchall("PRAGMA table_info(relations)")}
    assert {"confidence", "confidence_ai", "status", "page"} <= cols

    cols = {r["name"] for r in await db.execute_fetchall("PRAGMA table_info(papers)")}
    assert "text" in cols


async def test_migrate_preserves_existing_rows(db):
    now = "2026-08-04T00:00:00"
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
        "VALUES ('p1', '测试', 't.pdf', 1, 10, ?, 'done')", [now])
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES ('p1', 'abc', '概念A', '定义', 'finding', 1, 'ai', ?, ?)", [now, now])
    await db.commit()

    await database.migrate_schema(db)

    rows = await db.execute_fetchall("SELECT * FROM concepts WHERE slug='abc'")
    assert len(rows) == 1
    assert rows[0]["name"] == "概念A"
    assert rows[0]["confidence"] == 0.5   # 默认值
    assert rows[0]["status"] == "pending"
