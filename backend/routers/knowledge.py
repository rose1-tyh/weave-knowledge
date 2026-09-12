"""知识提取、图谱数据、CRUD、融合、搜索接口"""

import asyncio
import json
import os
import re
import uuid
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.schemas import (
    R, ExtractRequest, ConceptCreate, ConceptUpdate,
    RelationCreate, RelationUpdate, FusionRequest, MergeSuggestRequest,
    TextExtractRequest, UrlExtractRequest, EvidenceContextRequest,
)
from services.library_service import LibraryService
from services.parser_registry import get_parser_for_paper
from services.confidence_service import backfill_paper_confidences
from services.evidence_service import evidence_context_for_paper
from services.extraction_service import extraction_manager

router = APIRouter(prefix="/api", tags=["knowledge"])


# ── AI 提取（后台异步任务：SSE 实时进度 / 轮询降级 / 失败重试） ──

@router.post("/extract")
async def extract_knowledge(req: ExtractRequest):
    """对已上传的论文（PDF / DOCX）执行 AI 知识提取。

    提交后台任务后立即返回；进度经 SSE GET /extract/progress/{paper_id} 实时推送，
    或 GET /extract-status/{paper_id} 轮询查询。
    文本/URL 创建的论文（无 parser）若已有正文，同样可提交。
    """
    paper = await LibraryService.get_paper(req.paper_id)
    if paper is None:
        raise HTTPException(404, detail="论文不存在")
    parser = get_parser_for_paper(req.paper_id)
    if parser is not None and not os.path.exists(parser.get_path(req.paper_id)):
        raise HTTPException(404, detail="论文不存在")
    # 已完成且非空 → 幂等返回，不重复提取
    if paper["extract_status"] == "done" and paper["concept_count"] > 0:
        return R.success(data={"paperId": req.paper_id, "status": "done"})
    extraction_manager.submit(req.paper_id)
    return R.success(data={"paperId": req.paper_id, "status": "processing"})


@router.get("/extract-status/{paper_id}")
async def extract_status(paper_id: str):
    """查询论文提取任务状态：pending / processing / done / failed / not_found

    附带持久化的 stage/progress/detail/message/error（extract_tasks 表）。
    """
    return R.success(data=await extraction_manager.status(paper_id))


async def _progress_events(paper_id: str):
    """SSE 事件流：状态快照变化即推送，15s 心跳，终态后自动关闭（最长 20 分钟）"""
    last_payload = None
    idle = 0.0
    elapsed = 0.0
    while elapsed < 1200:
        snap = await extraction_manager.status(paper_id)
        if snap != last_payload:
            yield f"event: progress\ndata: {json.dumps(snap, ensure_ascii=False)}\n\n"
            last_payload = snap
            if snap["status"] in ("done", "failed", "not_found"):
                return
        await asyncio.sleep(0.5)
        idle += 0.5
        elapsed += 0.5
        if idle >= 15.0:
            yield ": keep-alive\n\n"
            idle = 0.0


@router.get("/extract/progress/{paper_id}")
async def extract_progress(paper_id: str):
    """SSE 实时提取进度：queued→parsing→extracting(i/n)→scoring→graphing→done/failed"""
    return StreamingResponse(
        _progress_events(paper_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/extract/{paper_id}/retry")
async def retry_extract(paper_id: str):
    """重试提取：重新提交后台任务（覆盖上次的任务记录与失败状态）"""
    paper = await LibraryService.get_paper(paper_id)
    if paper is None:
        raise HTTPException(404, detail="论文不存在")
    extraction_manager.retry(paper_id)
    return R.success(data={"paperId": paper_id, "status": "processing"})


# ── 文本/URL 提取 ──

@router.post("/extract-text")
async def extract_from_text(req: TextExtractRequest):
    """从粘贴的文本中提取知识（后台任务，立即返回 paperId）"""
    if not req.text.strip():
        raise HTTPException(400, detail="文本内容为空")

    paper_id = uuid.uuid4().hex[:12]
    await LibraryService.create_paper(
        paper_id=paper_id,
        title=req.title or "未命名知识",
        filename=f"{req.title or 'knowledge'}.txt",
        page_count=1,
        text_length=len(req.text),
    )
    await LibraryService.update_paper_text(paper_id, req.text)
    extraction_manager.submit(paper_id)
    return R.success(data={"paperId": paper_id, "status": "processing"})


def _fetch_url_text(url: str) -> tuple[str, str]:
    """同步抓取网页并清洗出正文（供线程池调用，避免阻塞事件循环）"""
    resp = requests.get(url, timeout=15, headers={
        "User-Agent": "Mozilla/5.0 (compatible; WeaveKnowledge/2.0)"
    })
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return title, "\n".join(lines)[:80000]


@router.post("/extract-url")
async def extract_from_url(req: UrlExtractRequest):
    """从网页链接抓取文本并提取知识"""
    if not req.url.strip():
        raise HTTPException(400, detail="URL 为空")

    # 抓取网页（线程池执行：requests + BS4 解析均为同步阻塞调用）
    try:
        title, text = await asyncio.to_thread(_fetch_url_text, req.url.strip())
    except Exception as e:
        raise HTTPException(400, detail=f"网页抓取失败: {str(e)}")

    paper_id = uuid.uuid4().hex[:12]
    await LibraryService.create_paper(
        paper_id=paper_id, title=title, filename=req.url,
        page_count=1, text_length=len(text),
    )
    await LibraryService.update_paper_text(paper_id, text)
    extraction_manager.submit(paper_id)
    return R.success(data={"paperId": paper_id, "status": "processing"})


@router.post("/papers/create-empty")
async def create_empty_paper(data: dict):
    """创建空白论文记录，用于手动构建知识"""
    title = data.get("title", "未命名知识")
    paper_id = uuid.uuid4().hex[:12]
    await LibraryService.create_paper(
        paper_id=paper_id, title=title, filename="manual",
        page_count=0, text_length=0,
    )
    await LibraryService.update_extract_status(paper_id, "done", 0, 0)
    return R.success(data={"paper_id": paper_id, "title": title})


# ── 图谱数据（已提取的论文） ──

@router.get("/graph/{paper_id}")
async def get_graph(paper_id: str):
    """获取已持久化的图谱数据"""
    data = await LibraryService.get_graph_data(paper_id)
    if not data:
        raise HTTPException(404, detail="图谱数据不存在，请先执行 AI 提取")
    return R.success(data=data)


# ── 概念 CRUD ──

@router.post("/graph/{paper_id}/concepts")
async def create_concept(paper_id: str, req: ConceptCreate):
    """手动添加概念"""
    import hashlib
    slug = hashlib.md5(req.name.encode()).hexdigest()[:8]
    now = datetime.now().isoformat()
    from database import get_db
    db = await get_db()
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'user', ?, ?)",
        [paper_id, slug, req.name, req.definition, req.type, req.page, now, now]
    )
    await db.commit()
    await LibraryService.update_extract_status(paper_id, "done")
    return R.success(data={"slug": slug})


@router.put("/graph/{paper_id}/concepts/{slug}")
async def update_concept(paper_id: str, slug: str, req: ConceptUpdate):
    """编辑概念"""
    from database import get_db
    db = await get_db()
    updates = []
    params = []
    for key in ["name", "definition", "type", "page", "status"]:
        val = getattr(req, key, None)
        if val is not None:
            updates.append(f"{key} = ?")
            params.append(val)
    if not updates:
        return R.success()
    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.extend([paper_id, slug])
    await db.execute(
        f"UPDATE concepts SET {', '.join(updates)} WHERE paper_id = ? AND slug = ?",
        params
    )
    await db.commit()
    return R.success()


@router.delete("/graph/{paper_id}/concepts/{slug}")
async def delete_concept(paper_id: str, slug: str):
    """删除概念（级联删除关联关系）"""
    from database import get_db
    db = await get_db()
    await db.execute("DELETE FROM relations WHERE paper_id = ? AND (source_slug = ? OR target_slug = ?)",
                     [paper_id, slug, slug])
    await db.execute("DELETE FROM concepts WHERE paper_id = ? AND slug = ?", [paper_id, slug])
    await db.commit()
    return R.success()


# ── 关系 CRUD ──

@router.post("/graph/{paper_id}/relations")
async def create_relation(paper_id: str, req: RelationCreate):
    """手动添加关系"""
    now = datetime.now().isoformat()
    from database import get_db
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO relations (paper_id, source_slug, target_slug, type, evidence, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, 'user', ?, ?)",
        [paper_id, req.source_slug, req.target_slug, req.type, req.evidence, now, now]
    )
    await db.commit()
    return R.success(data={"id": cursor.lastrowid})


@router.put("/graph/{paper_id}/relations/{rel_id}")
async def update_relation(paper_id: str, rel_id: int, req: RelationUpdate):
    """编辑关系"""
    from database import get_db
    db = await get_db()
    updates = []
    params = []
    if req.type is not None:
        updates.append("type = ?"); params.append(req.type)
    if req.evidence is not None:
        updates.append("evidence = ?"); params.append(req.evidence)
    if req.status is not None:
        updates.append("status = ?"); params.append(req.status)
    if not updates:
        return R.success()
    updates.append("updated_at = ?"); params.append(datetime.now().isoformat())
    params.extend([paper_id, rel_id])
    await db.execute(f"UPDATE relations SET {', '.join(updates)} WHERE paper_id = ? AND id = ?", params)
    await db.commit()
    return R.success()


@router.delete("/graph/{paper_id}/relations/{rel_id}")
async def delete_relation(paper_id: str, rel_id: int):
    """删除关系"""
    from database import get_db
    db = await get_db()
    await db.execute("DELETE FROM relations WHERE paper_id = ? AND id = ?", [paper_id, rel_id])
    await db.commit()
    return R.success()


# ── 论文管理 ──

@router.get("/library/papers")
async def list_papers(search: str = "", sort: str = "upload_time", page: int = 1, size: int = 50):
    """论文列表"""
    result = await LibraryService.list_papers(search, sort, page, size)
    return R.success(data=result)


@router.get("/library/papers/{paper_id}")
async def get_paper(paper_id: str):
    """论文详情"""
    paper = await LibraryService.get_paper(paper_id)
    if not paper:
        raise HTTPException(404, detail="论文不存在")
    return R.success(data=paper)


@router.patch("/library/papers/{paper_id}")
async def update_paper(paper_id: str, data: dict):
    """更新论文信息"""
    await LibraryService.update_paper(paper_id, data)
    return R.success()


@router.delete("/library/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """删除论文及关联数据"""
    await LibraryService.delete_paper(paper_id)
    return R.success()


# ── 统计 ──

@router.get("/stats")
async def get_stats():
    """仪表盘统计"""
    stats = await LibraryService.get_stats()
    return R.success(data=stats)


@router.get("/analytics/overview")
async def analytics_overview(paper_id: str = ""):
    """知识统计分析：类型构成、PageRank 核心概念、关系构成、跨论文重合度。

    不带 paper_id 时为全库视图（跨论文同名概念聚合为同一节点）。
    """
    from services.analytics_service import analytics_service
    return R.success(data=await analytics_service.overview(paper_id or None))


# ── 全局探索 ──

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
    """跨论文概念合并建议：精确同名 + 字符相似度（可选 embedding 精排）"""
    if len(req.paper_ids) < 2:
        raise HTTPException(400, detail="至少选择 2 篇论文")

    from database import get_db
    from services.similarity_service import (
        normalize, char_bigram_jaccard, concept_similarity, SIMILARITY_THRESHOLD,
    )
    from services.embedding_service import embedding_service

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
    from services.domain_constants import type_color
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


# ── 混合检索 ──

@router.get("/search")
async def hybrid_search(q: str = "", scope: str = "all", page: int = 1, size: int = 20):
    """混合检索：概念关键词 + 论文正文全文 + 语义向量三通道 RRF 融合排序。

    scope: all / concepts / fulltext；结果带 snippet 高亮（<mark> 标记）、
    命中通道列表与分页 total。未配置 embedding 时语义通道自动跳过。
    """
    from services.search_service import search_service
    return R.success(data=await search_service.search(q, scope, page, size))


# ── 导出 ──

from services.export_service import ExportService

@router.get("/export/{paper_id}/json")
async def export_json(paper_id: str):
    """导出知识图谱 JSON"""
    data = await ExportService.export_json(paper_id)
    if not data:
        raise HTTPException(404, detail="论文不存在")
    return R.success(data=data)


@router.get("/export/{paper_id}/markdown")
async def export_markdown(paper_id: str):
    """导出知识摘要 Markdown"""
    md = await ExportService.export_markdown(paper_id)
    return R.success(data=md)


@router.get("/export/{paper_id}/anki")
async def export_anki(paper_id: str):
    """导出 Anki 卡片包（.apkg 二进制流，前端以 blob 下载）"""
    from urllib.parse import quote
    result = await ExportService.export_anki(paper_id)
    if result is None:
        raise HTTPException(404, detail="论文不存在或无可导出概念")
    content, filename = result
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"deck.apkg\"; filename*=UTF-8''{quote(filename)}"},
    )


# ── 存量置信度回填 / 证据上下文 ──

@router.post("/system/backfill-confidence")
async def backfill_confidence(paper_id: str = ""):
    """存量论文置信度回填（纯文本信号）；指定 paper_id 则只处理该篇"""
    from database import get_db
    db = await get_db()
    if paper_id:
        ids = [paper_id]
    else:
        rows = await db.execute_fetchall("SELECT id FROM papers")
        ids = [r["id"] for r in rows]

    total_c = total_r = 0
    processed = 0
    for pid in ids:
        # 无正文且可解析的论文：补正文
        t = await db.execute_fetchall("SELECT text FROM papers WHERE id = ?", [pid])
        if not t or not t[0]["text"]:
            parser = get_parser_for_paper(pid)
            if parser:
                try:
                    parsed = parser.extract(pid)
                    await LibraryService.update_paper_text(pid, parsed["full_text"])
                except Exception:
                    continue
        result = await backfill_paper_confidences(db, pid)
        total_c += result["concepts"]; total_r += result["relations"]
        processed += 1
    return R.success(data={"processed": processed, "concepts": total_c, "relations": total_r})


@router.post("/system/reindex-embeddings")
async def reindex_embeddings():
    """全库重建概念向量索引（语义检索数据源）；未配置 embedding 时 skipped=True"""
    from database import get_db
    from services.embedding_service import embedding_service
    if not embedding_service.enabled:
        return R.success(data={"indexed": 0, "skipped": True})
    db = await get_db()
    rows = await db.execute_fetchall("SELECT paper_id, slug, name, definition FROM concepts")
    indexed = await embedding_service.index_concepts([dict(r) for r in rows])
    return R.success(data={"indexed": indexed})


@router.post("/papers/{paper_id}/evidence-context")
async def evidence_context(paper_id: str, req: EvidenceContextRequest):
    """返回证据串在原文中的上下文与页码；无正文/找不到时 found=False"""
    from database import get_db
    db = await get_db()
    return R.success(data=await evidence_context_for_paper(db, paper_id, req.evidence))
