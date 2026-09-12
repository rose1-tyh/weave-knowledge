"""全局探索接口 —— 多论文融合、合并建议、概念搜索、混合检索"""

import re
from datetime import datetime

from fastapi import APIRouter, HTTPException
from models.schemas import FusionRequest, MergeSuggestRequest, R
from services.domain_constants import type_color
from services.library_service import LibraryService

router = APIRouter(prefix="/api", tags=["explore"])


@router.post("/explore/fusion")
async def fusion_graph(req: FusionRequest):
    """多论文融合图谱"""
    if len(req.paper_ids) < 2:
        raise HTTPException(400, detail="至少选择 2 篇论文")

    all_concepts = {}
    all_relations = []
    title_parts = []

    for pid in req.paper_ids:
        paper = await LibraryService.get_paper(pid)
        if not paper:
            continue
        title_parts.append(paper["title"])
        gdata = await LibraryService.get_graph_data(pid)
        if not gdata:
            continue
        # slug → 概念名（用于把跨论文链接重映射到合并后的节点 id）
        slug_to_name = {n["id"]: n["name"] for n in gdata["nodes"]}
        # 合并节点，标记来源（剥离每篇论文的信任字段：融合视图无确认工作流，避免全部渲染成虚线/虚化）
        for node in gdata["nodes"]:
            clean = {k: v for k, v in node.items() if k not in ("status", "confidence", "confidence_ai", "evidence")}
            key = node["name"]
            if key not in all_concepts:
                all_concepts[key] = {**clean, "paperIds": [pid], "paperTitles": [paper["title"]]}
            else:
                if pid not in all_concepts[key]["paperIds"]:
                    all_concepts[key]["paperIds"].append(pid)
                    all_concepts[key]["paperTitles"].append(paper["title"])
        # 合并关系：source/target 按概念名重映射到合并节点的 id（同样剥离信任字段）
        for link in gdata["links"]:
            src_name = slug_to_name.get(link["source"], link["source"])
            tgt_name = slug_to_name.get(link["target"], link["target"])
            src_node = all_concepts.get(src_name)
            tgt_node = all_concepts.get(tgt_name)
            if src_node and tgt_node:
                clean = {k: v for k, v in link.items() if k not in ("status", "confidence", "confidence_ai", "page")}
                all_relations.append({**clean, "source": src_node["id"], "target": tgt_node["id"]})

    nodes = list(all_concepts.values())
    return R.success(data={
        "paperTitle": " · ".join(title_parts),
        "nodes": nodes,
        "links": all_relations,
    })


@router.post("/explore/merge-suggestions")
async def merge_suggestions(req: MergeSuggestRequest):
    """跨论文概念合并建议：精确同名 + 字符相似度（已落库向量余弦精排）"""
    if len(req.paper_ids) < 2:
        raise HTTPException(400, detail="至少选择 2 篇论文")

    from database import get_db
    from services.embedding_service import embedding_service
    from services.similarity_service import (
        SIMILARITY_THRESHOLD,
        char_bigram_jaccard,
        concept_similarity,
        normalize,
    )

    db = await get_db()

    # 收集各论文概念
    papers = []
    for pid in req.paper_ids:
        paper = await LibraryService.get_paper(pid)
        if not paper:
            continue
        rows = await db.execute_fetchall("SELECT * FROM concepts WHERE paper_id = ?", [pid])
        papers.append({"paper": paper, "concepts": [dict(r) for r in rows]})

    # 预载向量索引：候选精排用已落库向量做余弦，避免逐对实时调 HTTP（O(N²) HTTP → 0）
    vectors = await embedding_service.load_vectors([p["paper"]["id"] for p in papers])

    suggestions = []
    now = datetime.now().isoformat()

    # 两两论文比对：先精确同名（O(1) 查表），未命中再做相似度扫描
    for i in range(len(papers)):
        for j in range(i + 1, len(papers)):
            pa, pb = papers[i], papers[j]
            norm_map_b = {normalize(c["name"]): c for c in pb["concepts"]}
            for ca in pa["concepts"]:
                cb = norm_map_b.get(normalize(ca["name"]))
                matched_by = None
                if cb is not None:
                    # 原文完全一致 → exact；仅规范化后一致（如「知识图谱」vs「知识 图谱」）→ similar
                    matched_by = "exact" if ca["name"] == cb["name"] else "similar"
                else:
                    # 相似度扫描：bigram 取最优候选，已落库向量做余弦精排（未配置则纯 bigram）
                    best, best_sim = None, 0.0
                    for cand in pb["concepts"]:
                        s = char_bigram_jaccard(ca["name"], cand["name"])
                        if s > best_sim:
                            best, best_sim = cand, s
                    if best is not None:
                        emb_sim = None
                        va = vectors.get((pa["paper"]["id"], ca["slug"]))
                        vb = vectors.get((pb["paper"]["id"], best["slug"]))
                        if va and vb:
                            emb_sim = embedding_service.cosine(va, vb)
                        sim = concept_similarity(ca["name"], best["name"], emb_sim)
                        if sim >= SIMILARITY_THRESHOLD:
                            cb, matched_by = best, "similar"
                if not cb or matched_by is None:
                    continue
                confidence = 0.95 if matched_by == "exact" else 0.7
                suggestions.append({
                    "conceptName": ca["name"],
                    "paperIdA": pa["paper"]["id"], "paperTitleA": pa["paper"]["title"], "slugA": ca["slug"],
                    "paperIdB": pb["paper"]["id"], "paperTitleB": pb["paper"]["title"], "slugB": cb["slug"],
                    "confidence": confidence,
                    "matchedBy": matched_by,
                })
                await db.execute(
                    "INSERT OR REPLACE INTO concept_merges "
                    "(concept_name_a, paper_id_a, concept_name_b, paper_id_b, confidence, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [ca["name"], pa["paper"]["id"], cb["name"], pb["paper"]["id"], confidence, now]
                )

    await db.commit()
    return R.success(data={"suggestions": suggestions})


@router.get("/explore/search")
async def search_concepts(q: str = ""):
    """全局概念搜索（轻量版，概念通道）。

    ≥3 字符走 FTS5 trigram（中文子串匹配）；<3 字符回退 LIKE（trigram 限制）。
    查询串整体作为短语匹配并转义引号，避免 MATCH 语法注入。
    """
    if not q:
        return R.success(data={"results": []})
    from database import get_db
    db = await get_db()

    if len(q) >= 3:
        # FTS5 短语查询：剥离控制字符（引号/星号/括号/冒号/空白），整体包裹为短语，
        # 避免 MATCH 语法注入；trigram 下短语即连续子串匹配
        clean = re.sub(r'["*():\s]+', '', q)
        if not clean:
            return R.success(data={"results": []})
        fts_q = f'"{clean}"'
        rows = await db.execute_fetchall(
            """SELECT c.slug, c.name, c.type, c.definition, c.paper_id, p.title AS paper_title
               FROM concepts_fts f
               JOIN concepts c ON c.id = f.rowid
               JOIN papers p ON c.paper_id = p.id
               WHERE concepts_fts MATCH ?
               LIMIT 30""",
            [fts_q]
        )
    else:
        rows = await db.execute_fetchall(
            """SELECT c.slug, c.name, c.type, c.definition, c.paper_id, p.title AS paper_title
               FROM concepts c JOIN papers p ON c.paper_id = p.id
               WHERE c.name LIKE ? OR c.definition LIKE ?
               LIMIT 30""",
            [f"%{q}%", f"%{q}%"]
        )
    results = [{
        "id": r["slug"],
        "name": r["name"],
        "type": r["type"],
        "definition": r["definition"] or "",
        "color": type_color(r["type"]),
        "paperTitle": r["paper_title"],
        "paperId": r["paper_id"],
    } for r in [dict(r) for r in rows]]
    return R.success(data={"results": results})


@router.get("/search")
async def hybrid_search(q: str = "", scope: str = "all", page: int = 1, size: int = 20):
    """混合检索：概念关键词 + 论文正文全文 + 语义向量三通道 RRF 融合排序。

    scope: all / concepts / fulltext；结果带 snippet 高亮（<mark> 标记）、
    命中通道列表与分页 total。未配置 embedding 时语义通道自动跳过。
    """
    from services.search_service import search_service
    return R.success(data=await search_service.search(q, scope, page, size))
