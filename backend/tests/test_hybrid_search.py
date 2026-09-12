"""混合检索测试 —— papers_fts 触发器同步 / 三通道召回 / RRF 融合 / 分页 / 语义降级"""
import pytest

import database
from services.search_service import SearchService, rrf_fuse, sanitize_query
from services.embedding_service import embedding_service, pack_vector, unpack_vector


async def _seed_paper(db, pid, title, text=""):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
        "VALUES (?, ?, 'f.pdf', 1, ?, '2026-09-01', 'done', ?)", [pid, title, len(text), text])
    await db.commit()


async def _seed_concept(db, pid, slug, name, definition="", type_="finding"):
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 1, 'ai', '2026-09-01', '2026-09-01')", [pid, slug, name, definition, type_])
    await db.commit()


async def test_papers_fts_trigger_sync(db):
    """论文插入/更新 → papers_fts 触发器同步"""
    await _seed_paper(db, "p1", "知识图谱综述", "本文讨论知识图谱的构建方法")
    rows = await db.execute_fetchall("SELECT COUNT(*) AS c FROM papers_fts")
    assert rows[0]["c"] == 1

    await db.execute("UPDATE papers SET text = '神经网络新内容' WHERE id = 'p1'")
    await db.commit()
    hit = await db.execute_fetchall(
        "SELECT rowid FROM papers_fts WHERE papers_fts MATCH '\"神经网络\"'")
    assert len(hit) == 1


async def test_fulltext_channel_paper_hit(db):
    """正文通道：命中论文并返回 <mark> 高亮片段"""
    await _seed_paper(db, "p1", "综述", "本文提出知识图谱构建方法，知识图谱在学术场景应用广泛")
    svc = SearchService()
    result = await svc.search("知识图谱", scope="fulltext")
    assert result["total"] == 1
    hit = result["results"][0]
    assert hit["kind"] == "paper"
    assert hit["id"] == "p1"
    assert "<mark>" in hit["snippet"]
    assert result["channels"].get("fulltext") == 1


async def test_concept_channel_and_fusion(db):
    """概念通道命中 + 多通道融合（concepts 标记）"""
    await _seed_paper(db, "p1", "论文一")
    await _seed_concept(db, "p1", "aaa11111", "知识图谱", "一种知识表示方法")
    svc = SearchService()
    result = await svc.search("知识图谱", scope="concepts")
    assert result["total"] == 1
    hit = result["results"][0]
    assert hit["kind"] == "concept"
    assert "concepts" in hit["channels"]
    assert hit["paperId"] == "p1"


def test_rrf_fuse_ranks_multi_channel_hits_first():
    """RRF：双通道命中的条目排在单通道之前"""
    channels = {
        "concepts": [("k1", {"n": 1}), ("k2", {"n": 2})],
        "semantic": [("k2", {"n": 2}), ("k3", {"n": 3})],
    }
    fused = rrf_fuse(channels)
    top_key, top = max(fused.items(), key=lambda kv: kv[1]["score"])
    assert top_key == "k2"
    assert set(top["channels"]) == {"concepts", "semantic"}
    assert top["meta"]["n"] == 2


async def test_semantic_channel_with_stored_vectors(db, monkeypatch):
    """语义通道：读取已落库向量做余弦召回，与关键词通道融合"""
    await _seed_paper(db, "p1", "论文一")
    await _seed_concept(db, "p1", "k1", "知识图谱", "知识表示")
    await _seed_concept(db, "p1", "k2", "神经网络", "连接主义模型")

    # 伪造向量：k1 与查询同向（命中），k2 正交（不命中）
    await db.execute(
        "INSERT INTO concept_embeddings (paper_id, slug, model, dim, vector, updated_at) "
        "VALUES ('p1', 'k1', 'fake', 2, ?, '2026-09-01')", [pack_vector([1.0, 0.0])])
    await db.execute(
        "INSERT INTO concept_embeddings (paper_id, slug, model, dim, vector, updated_at) "
        "VALUES ('p1', 'k2', 'fake', 2, ?, '2026-09-01')", [pack_vector([0.0, 1.0])])
    await db.commit()

    monkeypatch.setattr(type(embedding_service), "enabled",
                        property(lambda self: True))

    async def fake_query(text):
        return [1.0, 0.0]

    monkeypatch.setattr(embedding_service, "embed_query", fake_query)

    svc = SearchService()
    result = await svc.search("表示学习", scope="concepts")
    ids = [r["id"] for r in result["results"]]
    assert "k1" in ids
    assert "k2" not in ids
    k1 = next(r for r in result["results"] if r["id"] == "k1")
    assert "semantic" in k1["channels"]


async def test_semantic_channel_degrades_without_config(db, monkeypatch):
    """未配置 embedding → 语义通道跳过，仅关键词通道"""
    await _seed_paper(db, "p1", "论文一")
    await _seed_concept(db, "p1", "k1", "知识图谱", "知识表示")
    monkeypatch.setattr(type(embedding_service), "enabled", property(lambda self: False))

    svc = SearchService()
    result = await svc.search("知识图谱", scope="all")
    assert all("semantic" not in r["channels"] for r in result["results"])
    assert result["total"] == 1


async def test_pagination_and_total(db):
    """分页与 total 一致"""
    await _seed_paper(db, "p1", "论文一")
    for i in range(5):
        await _seed_concept(db, "p1", f"slug{i:04d}", f"数据集{i}")
    svc = SearchService()
    page1 = await svc.search("数据", scope="concepts", page=1, size=2)
    page3 = await svc.search("数据", scope="concepts", page=3, size=2)
    assert page1["total"] == 5
    assert len(page1["results"]) == 2
    assert page3["page"] == 3
    assert len(page3["results"]) == 1


async def test_query_syntax_characters_sanitized(db):
    """MATCH 语法字符被净化，不抛异常且仍可命中"""
    await _seed_paper(db, "p1", "论文一")
    await _seed_concept(db, "p1", "k1", "知识图谱", "知识表示")
    svc = SearchService()
    result = await svc.search('知"识*图:谱( )', scope="concepts")
    assert result["total"] == 1


async def test_fts_rebuild_only_when_stale(db):
    """按需重建：FTS 与主表计数不一致时 init_db 修复；一致时不动"""
    await _seed_paper(db, "p1", "论文一", "正文内容")

    # 制造失同步：向 FTS 插入幽灵行 → init_db 重建后消失
    await db.execute("INSERT INTO papers_fts(rowid, title, text) VALUES (99999, '幽灵', '幽灵')")
    await db.commit()
    await database.init_db()
    ghost = await db.execute_fetchall(
        "SELECT rowid FROM papers_fts WHERE papers_fts MATCH '\"幽灵\"'")
    assert not ghost
    cnt = await db.execute_fetchall("SELECT COUNT(*) AS c FROM papers_fts")
    papers_cnt = await db.execute_fetchall("SELECT COUNT(*) AS c FROM papers")
    assert cnt[0]["c"] == papers_cnt[0]["c"]


async def test_search_route_registered():
    from main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/search" in paths
    assert "/api/system/reindex-embeddings" in paths


def test_pack_unpack_vector_roundtrip():
    vec = [0.25, -0.5, 1.0]
    assert unpack_vector(pack_vector(vec)) == pytest.approx(vec, abs=1e-6)
