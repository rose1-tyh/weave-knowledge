from services.evidence_service import evidence_context_for_paper, locate_evidence

TEXT = "[第1页]\n引言 本文介绍图谱。\n\n[第2页]\n图谱是知识结构。证据在这里出现。\n\n[第3页]\n结论。"


def test_locate_exact():
    loc = locate_evidence(TEXT, "图谱是知识结构")
    assert loc is not None
    assert loc["page"] == 2
    assert 0 <= loc["start"] < loc["end"] <= len(loc["context"])
    assert "图谱是知识结构" in loc["context"][loc["start"]:loc["end"]]


def test_locate_not_found():
    assert locate_evidence(TEXT, "完全不存在的概念") is None


def test_locate_empty_input():
    assert locate_evidence(TEXT, "") is None
    assert locate_evidence("", "x") is None


def test_locate_whitespace_tolerant():
    loc = locate_evidence(TEXT, "图谱是  知识 结构")
    assert loc is not None
    assert loc["page"] == 2


async def test_evidence_context_found(db):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
        "VALUES ('p1','t','t.pdf',1,0,'2026-08-04','done','[第1页]\\n图谱是知识结构。')")
    await db.commit()
    result = await evidence_context_for_paper(db, "p1", "图谱是知识结构")
    assert result["found"] is True
    assert result["page"] == 1


async def test_evidence_context_missing_text(db):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
        "VALUES ('p1','t','t.pdf',1,0,'2026-08-04','done')")
    await db.commit()
    result = await evidence_context_for_paper(db, "p1", "x")
    assert result["found"] is False
