"""FTS5 全文搜索测试 —— trigram 中文子串匹配 / 短查询回退 / 触发器同步 / 特殊字符转义"""



async def _seed(db, paper_id="p1", concept="知识图谱", definition="关于知识结构的表示方法"):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
        "VALUES (?, 't', 't.pdf', 1, 0, '2026-08-04', 'done')", [paper_id])
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES (?, 'abc12345', ?, ?, 'method', 1, 'ai', '2026-08-04', '2026-08-04')",
        [paper_id, concept, definition])
    await db.commit()


async def test_fts_matches_chinese_substring(db):
    """≥3 字符查询走 FTS，命中中文子串"""
    await _seed(db)
    from database import get_db
    d = await get_db()
    rows = await d.execute_fetchall(
        """SELECT c.slug FROM concepts_fts f
           JOIN concepts c ON c.id = f.rowid
           WHERE concepts_fts MATCH ?""",
        ['"识图谱"'])
    assert len(rows) == 1


async def test_fts_matches_definition(db):
    """查询命中 definition 列"""
    await _seed(db)
    from database import get_db
    d = await get_db()
    rows = await d.execute_fetchall(
        """SELECT c.slug FROM concepts_fts f
           JOIN concepts c ON c.id = f.rowid
           WHERE concepts_fts MATCH ?""",
        ['"知识结构"'])
    assert len(rows) == 1


async def test_delete_concept_syncs_fts(db):
    """删除概念后 FTS 索引同步删除（触发器）"""
    await _seed(db)
    from database import get_db
    d = await get_db()
    await d.execute("DELETE FROM concepts WHERE slug = 'abc12345'")
    await d.commit()
    rows = await d.execute_fetchall(
        """SELECT c.slug FROM concepts_fts f
           JOIN concepts c ON c.id = f.rowid
           WHERE concepts_fts MATCH ?""",
        ['"识图谱"'])
    assert len(rows) == 0


async def test_delete_paper_cascade_syncs_fts(db):
    """删除论文（级联删概念）后 FTS 索引同步"""
    await _seed(db)
    from database import get_db
    d = await get_db()
    await d.execute("DELETE FROM papers WHERE id = 'p1'")
    await d.commit()
    rows = await d.execute_fetchall("SELECT rowid FROM concepts_fts WHERE concepts_fts MATCH ?", ['"识图谱"'])
    assert len(rows) == 0


async def test_short_query_falls_back_to_like(db):
    """<3 字符查询回退 LIKE（trigram 无法匹配短串）"""
    await _seed(db)
    from database import get_db
    d = await get_db()
    rows = await d.execute_fetchall(
        "SELECT slug FROM concepts WHERE name LIKE ?", ["%图%"])
    assert len(rows) == 1


async def test_quote_in_query_does_not_break(db):
    """含引号的查询不触发 MATCH 语法错误（search_concepts 剥离控制字符）"""
    await _seed(db, concept='知识图谱')
    from routers.explore import search_concepts
    result = await search_concepts('知识"图谱')
    # 不抛异常；剥离引号后短语匹配命中概念名
    assert result.data["results"], "剥离控制字符后应命中概念"
