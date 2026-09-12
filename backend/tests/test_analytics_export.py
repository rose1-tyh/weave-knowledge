"""统计分析 + Anki 导出测试 —— PageRank / 类型构成 / 跨论文重合 / .apkg 生成"""
from services.analytics_service import AnalyticsService, pagerank
from services.export_service import ExportService


async def _seed_paper(db, pid, title):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
        "VALUES (?, ?, 'f.pdf', 1, 0, '2026-09-01', 'done', '')", [pid, title])
    await db.commit()


async def _seed_concept(db, pid, slug, name, type_="finding"):
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, 'd', ?, 1, 'ai', '2026-09-01', '2026-09-01')", [pid, slug, name, type_])
    await db.commit()


async def _seed_relation(db, pid, src, tgt, type_="supports"):
    await db.execute(
        "INSERT INTO relations (paper_id, source_slug, target_slug, type, evidence, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, 'e', 'ai', '2026-09-01', '2026-09-01')", [pid, src, tgt, type_])
    await db.commit()


def test_pagerank_hub_dominates():
    """星型图：被多条边指向的枢纽节点排名最高"""
    ranks = pagerank(
        ["hub", "a", "b", "c"],
        [("a", "hub", 1.0), ("b", "hub", 1.0), ("c", "hub", 1.0)])
    assert ranks["hub"] == max(ranks.values())
    assert ranks["hub"] > sum(ranks[v] for v in ("a", "b", "c")) / 3


def test_pagerank_dangling_mass_redistributed():
    """悬挂节点（无出边）的质量重新分配，总秩恒为 1"""
    ranks = pagerank(["x", "y", "z"], [("x", "y", 1.0)])
    assert abs(sum(ranks.values()) - 1.0) < 1e-6
    # y 有入边 → 排名高于悬挂的 z
    assert ranks["y"] > ranks["z"]


def test_pagerank_empty_graph():
    assert pagerank([], []) == {}


async def test_overview_global_aggregates_and_overlap(db):
    """全库视图：类型构成 + PageRank 核心概念 + 跨论文同名重合"""
    await _seed_paper(db, "p1", "论文一")
    await _seed_paper(db, "p2", "论文二")
    # p1：知识图谱 为枢纽（3 条入边），跨 p1/p2 同名
    await _seed_concept(db, "p1", "s1", "知识图谱", "theory")
    await _seed_concept(db, "p1", "s2", "方法A", "method")
    await _seed_concept(db, "p2", "s3", "知识图谱", "theory")
    await _seed_concept(db, "p2", "s4", "数据集B", "dataset")
    await _seed_relation(db, "p1", "s2", "s1")
    await _seed_relation(db, "p1", "s2", "s1", "uses")
    await _seed_relation(db, "p2", "s4", "s3")

    result = await AnalyticsService().overview()
    assert result["scope"] == "all"
    assert result["totals"]["concepts"] == 4
    assert result["totals"]["relations"] == 3
    assert result["totals"]["papers"] == 2

    types = {t["type"]: t["count"] for t in result["conceptTypes"]}
    assert types["theory"] == 2 and types["method"] == 1

    # 核心概念：知识图谱（2 个不同邻居 + 跨论文）应排第一
    assert result["keyConcepts"][0]["name"] == "知识图谱"
    assert result["keyConcepts"][0]["degree"] == 2
    assert len(result["keyConcepts"][0]["paperIds"]) == 2

    # 跨论文重合：知识图谱出现在两篇
    assert any(o["name"] == "知识图谱" and len(o["paperIds"]) == 2
               for o in result["crossPaperOverlap"])


async def test_overview_single_paper_scope(db):
    """单篇视图：只统计该篇，且不返回全库 papers 列表"""
    await _seed_paper(db, "p1", "论文一")
    await _seed_paper(db, "p2", "论文二")
    await _seed_concept(db, "p1", "s1", "概念X")
    await _seed_concept(db, "p2", "s2", "概念Y")

    result = await AnalyticsService().overview("p1")
    assert result["scope"] == "p1"
    assert result["totals"]["concepts"] == 1
    assert "papers" not in result


async def test_anki_export_generates_apkg(db):
    """Anki 导出：生成合法 .apkg（zip 魔数）"""
    await _seed_paper(db, "p1", "测试论文")
    await _seed_concept(db, "p1", "s1", "知识图谱", "theory")
    await _seed_concept(db, "p1", "s2", "方法A", "method")
    await _seed_relation(db, "p1", "s2", "s1")

    result = await ExportService.export_anki("p1")
    assert result is not None
    content, filename = result
    assert content[:2] == b"PK"          # zip 魔数（.apkg 本质是 zip）
    assert filename.endswith(".apkg")
    assert len(content) > 500


async def test_anki_export_missing_paper(db):
    assert await ExportService.export_anki("nope") is None


async def test_anki_export_empty_concepts(db):
    """论文存在但无概念 → None（无可导出）"""
    await _seed_paper(db, "p-empty", "空论文")
    assert await ExportService.export_anki("p-empty") is None


def test_analytics_and_anki_routes_registered():
    from main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/analytics/overview" in paths
    assert "/api/export/{paper_id}/anki" in paths
