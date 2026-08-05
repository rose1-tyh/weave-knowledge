from services.library_service import LibraryService


async def _seed_paper(db, pid="p1", with_text=""):
    if with_text:
        await db.execute(
            "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
            "VALUES (?, 't', 't.pdf', 1, 0, '2026-08-04', 'done', ?)", [pid, with_text])
    else:
        await db.execute(
            "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
            "VALUES (?, 't', 't.pdf', 1, 0, '2026-08-04', 'done')", [pid])
    await db.commit()


async def test_save_concepts_persists_new_fields(db):
    await _seed_paper(db)
    await LibraryService.save_concepts("p1", [{
        "id": "abc", "name": "图谱", "definition": "d", "type": "finding", "page": 2,
        "evidence": "证据", "confidence": 0.6, "confidence_ai": 0.9, "status": "pending",
    }])
    rows = await db.execute_fetchall("SELECT * FROM concepts WHERE slug='abc'")
    assert rows[0]["confidence"] == 0.6
    assert rows[0]["confidence_ai"] == 0.9
    assert rows[0]["evidence"] == "证据"
    assert rows[0]["status"] == "pending"


async def test_save_relations_persists_new_fields(db):
    await _seed_paper(db)
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES ('p1','a','A','', 'finding', 1, 'ai', '2026-08-04', '2026-08-04'), "
        "('p1','b','B','', 'finding', 1, 'ai', '2026-08-04', '2026-08-04')")
    await db.commit()
    await LibraryService.save_relations("p1", [{
        "source": "a", "target": "b", "type": "cites", "evidence": "e",
        "page": 3, "confidence": 0.7, "confidence_ai": 0.8, "status": "pending",
    }])
    rows = await db.execute_fetchall("SELECT * FROM relations")
    assert rows[0]["confidence"] == 0.7
    assert rows[0]["confidence_ai"] == 0.8
    assert rows[0]["page"] == 3


async def test_update_paper_text(db):
    await _seed_paper(db)
    await LibraryService.update_paper_text("p1", "全文内容")
    rows = await db.execute_fetchall("SELECT text FROM papers WHERE id='p1'")
    assert rows[0]["text"] == "全文内容"


async def test_get_graph_data_includes_new_fields(db):
    await _seed_paper(db, with_text="[第1页]\n图谱 图谱 图谱")
    await LibraryService.save_concepts("p1", [{
        "id": "abc", "name": "图谱", "definition": "d", "type": "finding", "page": 1,
        "evidence": "证据", "confidence": 0.6, "confidence_ai": 0.9, "status": "confirmed",
    }])
    data = await LibraryService.get_graph_data("p1")
    node = data["nodes"][0]
    assert node["confidence"] == 0.6
    assert node["confidence_ai"] == 0.9
    assert node["status"] == "confirmed"
    assert node["evidence"] == "证据"


async def test_list_papers_excludes_text(db):
    """列表接口不返回 text 大字段"""
    await _seed_paper(db, with_text="全文内容" * 1000)
    result = await LibraryService.list_papers()
    assert result["total"] == 1
    paper = result["papers"][0]
    assert "text" not in paper
    assert paper["id"] == "p1"
    assert paper["title"] == "t"


async def test_get_paper_excludes_text_keeps_counts(db):
    """详情接口不返回 text，但保留概念/关系计数"""
    await _seed_paper(db, with_text="全文内容")
    await LibraryService.save_concepts("p1", [{
        "id": "abc", "name": "图谱", "definition": "d", "type": "finding", "page": 1,
    }])
    paper = await LibraryService.get_paper("p1")
    assert paper is not None
    assert "text" not in paper
    assert paper["concept_count"] == 1
    assert paper["relation_count"] == 0
