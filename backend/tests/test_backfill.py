from services.confidence_service import backfill_paper_confidences


async def test_backfill_recomputes_confidence(db):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
        "VALUES ('p1','t','t.pdf',1,0,'2026-08-04','done','[第1页]\n图谱 图谱 图谱')")
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, confidence, confidence_ai, status, created_by, created_at, updated_at) "
        "VALUES ('p1','abc','图谱','d','finding',1,0.9,0.9,'pending','ai','2026-08-04','2026-08-04')")
    await db.commit()

    result = await backfill_paper_confidences(db, "p1")
    assert result["concepts"] == 1
    rows = await db.execute_fetchall("SELECT confidence, confidence_ai FROM concepts WHERE slug='abc'")
    assert rows[0]["confidence_ai"] is None
    assert rows[0]["confidence"] > 0.5  # 纯文本信号重算（正文出现 3 次 → 高信号）


async def test_backfill_skips_without_text(db):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
        "VALUES ('p1','t','t.pdf',1,0,'2026-08-04','done')")
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, confidence, confidence_ai, status, created_by, created_at, updated_at) "
        "VALUES ('p1','abc','图谱','d','finding',1,0.9,0.9,'pending','ai','2026-08-04','2026-08-04')")
    await db.commit()

    result = await backfill_paper_confidences(db, "p1")
    assert result["concepts"] == 0  # 无正文 → 跳过
