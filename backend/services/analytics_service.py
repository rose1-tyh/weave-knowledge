"""统计分析服务 —— 概念/关系构成、PageRank 核心概念、跨论文重合度

PageRank 为纯 Python 实现（幂迭代 + dangling 质量重分布），节点以规范化概念名
聚合：全局视图下跨论文同名概念合并为同一节点，排名反映概念在知识网络中的
真实枢纽程度，而非单篇内的局部计数。
"""

from collections import defaultdict

from services.domain_constants import type_label, rel_label, type_color
from services.similarity_service import normalize


def pagerank(nodes: list, weighted_edges: list[tuple],
             damping: float = 0.85, max_iter: int = 100, tol: float = 1e-6) -> dict:
    """纯 Python PageRank。

    nodes: 节点键列表；weighted_edges: [(src, dst, weight)]（重边按权重累加）。
    返回 {node: rank}，rank 归一化到总和 1。
    """
    n = len(nodes)
    if n == 0:
        return {}
    out_weight = defaultdict(float)
    incoming = defaultdict(list)
    for s, d, w in weighted_edges:
        out_weight[s] += w
        incoming[d].append((s, w))

    rank = {v: 1.0 / n for v in nodes}
    for _ in range(max_iter):
        dangling = sum(rank[v] for v in nodes if out_weight[v] == 0)
        base = (1.0 - damping) / n + damping * dangling / n
        new = {}
        for v in nodes:
            s = base
            for src, w in incoming[v]:
                if out_weight[src] > 0:
                    s += damping * rank[src] * w / out_weight[src]
            new[v] = s
        err = sum(abs(new[v] - rank[v]) for v in nodes)
        rank = new
        if err < tol:
            break
    total = sum(rank.values()) or 1.0
    return {v: r / total for v, r in rank.items()}


class AnalyticsService:
    """全库 / 单篇知识统计分析"""

    KEY_CONCEPTS_TOP = 8
    OVERLAP_TOP = 10

    async def overview(self, paper_id: str | None = None) -> dict:
        from database import get_db
        db = await get_db()

        scope_where, scope_params = "", []
        if paper_id:
            scope_where = " WHERE paper_id = ?"
            scope_params = [paper_id]

        concept_rows = [dict(r) for r in await db.execute_fetchall(
            f"SELECT paper_id, slug, name, type FROM concepts{scope_where}", scope_params)]
        relation_rows = [dict(r) for r in await db.execute_fetchall(
            f"SELECT paper_id, source_slug, target_slug, type FROM relations{scope_where}", scope_params)]

        # ── 类型构成 ──
        type_counts = defaultdict(int)
        for c in concept_rows:
            type_counts[c["type"]] += 1
        concept_types = [{
            "type": t, "label": type_label(t), "count": n,
            "color": type_color(t),
        } for t, n in sorted(type_counts.items(), key=lambda kv: -kv[1])]

        rel_counts = defaultdict(int)
        for r in relation_rows:
            rel_counts[r["type"]] += 1
        relation_types = [{
            "type": t, "label": rel_label(t), "count": n,
        } for t, n in sorted(rel_counts.items(), key=lambda kv: -kv[1])]

        # ── 图分析：节点按规范化概念名聚合（跨论文同名合并），重边计权重 ──
        slug_to_key = {(c["paper_id"], c["slug"]): normalize(c["name"]) for c in concept_rows}
        node_meta: dict[str, dict] = {}
        for c in concept_rows:
            key = slug_to_key[(c["paper_id"], c["slug"])]
            meta = node_meta.setdefault(key, {"name": c["name"], "paperIds": set()})
            meta["paperIds"].add(c["paper_id"])

        edges = defaultdict(float)
        for r in relation_rows:
            src = slug_to_key.get((r["paper_id"], r["source_slug"]))
            tgt = slug_to_key.get((r["paper_id"], r["target_slug"]))
            if src and tgt and src != tgt:
                edges[(src, tgt)] += 1.0

        node_list = list(node_meta.keys())
        weighted = [(s, d, w) for (s, d), w in edges.items()]
        ranks = pagerank(node_list, weighted)
        degree = defaultdict(int)
        for s, d in edges:
            degree[s] += 1
            degree[d] += 1

        key_concepts = [{
            "name": node_meta[v]["name"],
            "paperIds": sorted(node_meta[v]["paperIds"]),
            "pagerank": round(ranks[v], 4),
            "degree": degree[v],
        } for v in sorted(node_list, key=lambda v: -ranks[v])[:self.KEY_CONCEPTS_TOP]]

        # ── 跨论文概念重合（规范化同名出现在 ≥2 篇） ──
        overlap: dict[str, dict] = {}
        for key, meta in node_meta.items():
            if len(meta["paperIds"]) >= 2:
                overlap[key] = {"name": meta["name"], "paperIds": sorted(meta["paperIds"])}
        cross_overlap = sorted(overlap.values(), key=lambda m: -len(m["paperIds"]))[:self.OVERLAP_TOP]

        # ── 汇总 ──
        totals = {"concepts": len(concept_rows), "relations": len(relation_rows)}
        if not paper_id:
            pc = await db.execute_fetchall("SELECT COUNT(*) AS c FROM papers")
            totals["papers"] = pc[0]["c"] if pc else 0

        result = {
            "scope": paper_id or "all",
            "totals": totals,
            "conceptTypes": concept_types,
            "relationTypes": relation_types,
            "keyConcepts": key_concepts,
            "crossPaperOverlap": cross_overlap,
        }
        if not paper_id:
            # 全库视图附带各论文贡献（时间线/条形用）
            paper_rows = [dict(r) for r in await db.execute_fetchall(
                "SELECT id, title, upload_time, concept_count, relation_count FROM papers "
                "ORDER BY upload_time DESC LIMIT 20")]
            result["papers"] = [{
                "id": p["id"], "title": p["title"], "uploadTime": p["upload_time"],
                "conceptCount": p["concept_count"], "relationCount": p["relation_count"],
            } for p in paper_rows]
        return result


# 全局单例
analytics_service = AnalyticsService()
