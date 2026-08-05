"""相似度服务与合并建议测试 —— bigram Jaccard / 阈值 / embedding 回退 / merge 集成"""

import pytest
from services.similarity_service import (
    normalize, char_bigram_jaccard, concept_similarity, SIMILARITY_THRESHOLD,
)


def test_normalize_strips_noise():
    assert normalize("知识 图谱") == normalize("知识图谱")
    assert normalize("Knowledge-Graph") == normalize("knowledgegraph")
    assert normalize("（图谱）") == "图谱"


def test_bigram_jaccard_identical():
    assert char_bigram_jaccard("知识图谱", "知识图谱") == 1.0


def test_bigram_jaccard_near_similar():
    # 「知识 图谱」vs「知识图谱」→ 规范化后相同 → 1.0
    assert char_bigram_jaccard("知识 图谱", "知识图谱") == 1.0
    # 「知识图」vs「知识图谱」→ 高度相似（超阈值）
    sim = char_bigram_jaccard("知识图", "知识图谱")
    assert sim > SIMILARITY_THRESHOLD


def test_bigram_jaccard_unrelated():
    assert char_bigram_jaccard("深度学习", "唐朝历史") < SIMILARITY_THRESHOLD


def test_concept_similarity_exact():
    assert concept_similarity("知识图谱", "知识图谱") == 1.0
    assert concept_similarity("知识 图谱", "知识图谱") == 1.0  # 规范化后相等


def test_concept_similarity_falls_back_without_embedding():
    sim = concept_similarity("图谱构建", "知识图谱构建", None)
    assert sim > 0


def test_concept_similarity_blends_embedding():
    # embedding 提供时加权（0.5 bigram + 0.5 emb），结果 round 到 3 位
    sim = concept_similarity("A概念", "B概念", 0.8)
    expected = round(0.5 * char_bigram_jaccard("A概念", "B概念") + 0.5 * 0.8, 3)
    assert sim == expected


async def test_merge_suggestions_exact_and_similar(db):
    """merge_suggestions：完全同名 → exact/0.95；仅规范化一致 → similar/0.7"""
    from routers.knowledge import merge_suggestions
    from models.schemas import MergeSuggestRequest

    for pid, title in [("p1", "论文一"), ("p2", "论文二")]:
        await db.execute(
            "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
            "VALUES (?, ?, 't.pdf', 1, 0, '2026-08-04', 'done')", [pid, title])
    for pid, slug, name in [
        ("p1", "a1", "知识图谱"), ("p1", "a2", "深度学习"),
        ("p2", "b1", "知识 图谱"), ("p2", "b2", "深度学习"),
    ]:
        await db.execute(
            "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
            "VALUES (?, ?, ?, '', 'finding', 1, 'ai', '2026-08-04', '2026-08-04')", [pid, slug, name])
    await db.commit()

    result = await merge_suggestions(MergeSuggestRequest(paper_ids=["p1", "p2"]))
    sugs = result.data["suggestions"]
    by_name = {s["conceptName"]: s for s in sugs}
    assert by_name["深度学习"]["matchedBy"] == "exact"
    assert by_name["深度学习"]["confidence"] == 0.95
    assert by_name["知识图谱"]["matchedBy"] == "similar"
    assert by_name["知识图谱"]["confidence"] == 0.7


async def test_merge_suggestions_unrelated_not_suggested(db):
    """无关概念不产生合并建议"""
    from routers.knowledge import merge_suggestions
    from models.schemas import MergeSuggestRequest

    for pid, title in [("p1", "论文一"), ("p2", "论文二")]:
        await db.execute(
            "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
            "VALUES (?, ?, 't.pdf', 1, 0, '2026-08-04', 'done')", [pid, title])
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES ('p1', 'a1', '深度学习', '', 'finding', 1, 'ai', '2026-08-04', '2026-08-04')")
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES ('p2', 'b1', '唐朝历史', '', 'finding', 1, 'ai', '2026-08-04', '2026-08-04')")
    await db.commit()

    result = await merge_suggestions(MergeSuggestRequest(paper_ids=["p1", "p2"]))
    assert result.data["suggestions"] == []
