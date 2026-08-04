"""知识提取、图谱数据、CRUD、融合、搜索接口"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from models.schemas import (
    R, ExtractRequest, ConceptCreate, ConceptUpdate,
    RelationCreate, RelationUpdate, FusionRequest, MergeSuggestRequest,
    TextExtractRequest, UrlExtractRequest, EvidenceContextRequest,
)
from services.ai_service import AIService
from services.graph_service import GraphService
from services.library_service import LibraryService
from services.parser_registry import get_parser_for_paper
from services.confidence_service import backfill_paper_confidences
from services.evidence_service import evidence_context_for_paper
import uuid
import requests
from bs4 import BeautifulSoup

router = APIRouter(prefix="/api", tags=["knowledge"])
ai_service = AIService()


def _relations_with_slugs(graph) -> list[dict]:
    """把 AI 提取的关系中的概念名重映射为 slug，保证与手动关系存储一致"""
    name_to_slug = {c.name: c.id for c in graph.concepts}
    result = []
    for r in graph.relations:
        rd = r.model_dump()
        rd["source"] = name_to_slug.get(rd["source"], rd["source"])
        rd["target"] = name_to_slug.get(rd["target"], rd["target"])
        result.append(rd)
    return result


# ── AI 提取 ──

@router.post("/extract")
async def extract_knowledge(req: ExtractRequest):
    """对已上传的论文（PDF / DOCX）执行 AI 知识提取，结果写入 DB"""
    parser = get_parser_for_paper(req.paper_id)
    if parser is None:
        raise HTTPException(404, detail="论文不存在")
    try:
        paper = parser.extract(req.paper_id)
    except FileNotFoundError:
        raise HTTPException(404, detail="论文不存在")

    await LibraryService.update_paper_text(req.paper_id, paper["full_text"])
    await LibraryService.update_extract_status(req.paper_id, "processing")

    try:
        raw = ai_service.extract_knowledge(paper["full_text"], paper["title"])
        graph = GraphService.build_graph(raw, paper["title"])

        if not graph.concepts:
            await LibraryService.update_extract_status(req.paper_id, "failed")
            return R.error("未能提取到概念")

        # 存库
        concepts_data = [c.model_dump() for c in graph.concepts]
        relations_data = _relations_with_slugs(graph)
        await LibraryService.save_concepts(req.paper_id, concepts_data)
        await LibraryService.save_relations(req.paper_id, relations_data)
        await LibraryService.update_extract_status(
            req.paper_id, "done", len(concepts_data), len(relations_data)
        )

        d3_data = GraphService.to_d3_format(graph)
        return R.success(data=d3_data)
    except Exception as e:
        await LibraryService.update_extract_status(req.paper_id, "failed")
        raise HTTPException(500, detail=f"AI 提取失败: {str(e)}")


# ── 文本/URL 提取 ──

@router.post("/extract-text")
async def extract_from_text(req: TextExtractRequest):
    """从粘贴的文本中提取知识"""
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
    await LibraryService.update_extract_status(paper_id, "processing")

    try:
        raw = ai_service.extract_knowledge(req.text, req.title or "文本知识")
        graph = GraphService.build_graph(raw, req.title or "文本知识")
        if not graph.concepts:
            await LibraryService.update_extract_status(paper_id, "failed")
            return R.error("未能提取到概念")

        concepts_data = [c.model_dump() for c in graph.concepts]
        relations_data = _relations_with_slugs(graph)
        await LibraryService.save_concepts(paper_id, concepts_data)
        await LibraryService.save_relations(paper_id, relations_data)
        await LibraryService.update_extract_status(paper_id, "done", len(concepts_data), len(relations_data))

        d3_data = GraphService.to_d3_format(graph)
        d3_data["paperId"] = paper_id
        return R.success(data=d3_data)
    except Exception as e:
        await LibraryService.update_extract_status(paper_id, "failed")
        raise HTTPException(500, detail=f"AI 提取失败: {str(e)}")


@router.post("/extract-url")
async def extract_from_url(req: UrlExtractRequest):
    """从网页链接抓取文本并提取知识"""
    if not req.url.strip():
        raise HTTPException(400, detail="URL 为空")

    # 抓取网页
    try:
        resp = requests.get(req.url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; WeaveKnowledge/2.0)"
        })
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
    except Exception as e:
        raise HTTPException(400, detail=f"网页抓取失败: {str(e)}")

    # 提取文本
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    text = "\n".join(lines)[:80000]  # 限制长度
    title = soup.title.string.strip() if soup.title else req.url

    paper_id = uuid.uuid4().hex[:12]
    await LibraryService.create_paper(
        paper_id=paper_id, title=title, filename=req.url,
        page_count=1, text_length=len(text),
    )
    await LibraryService.update_paper_text(paper_id, text)
    await LibraryService.update_extract_status(paper_id, "processing")

    try:
        raw = ai_service.extract_knowledge(text, title)
        graph = GraphService.build_graph(raw, title)
        if not graph.concepts:
            await LibraryService.update_extract_status(paper_id, "failed")
            return R.error("未能提取到概念")

        concepts_data = [c.model_dump() for c in graph.concepts]
        relations_data = _relations_with_slugs(graph)
        await LibraryService.save_concepts(paper_id, concepts_data)
        await LibraryService.save_relations(paper_id, relations_data)
        await LibraryService.update_extract_status(paper_id, "done", len(concepts_data), len(relations_data))

        d3_data = GraphService.to_d3_format(graph)
        d3_data["paperId"] = paper_id
        return R.success(data=d3_data)
    except Exception as e:
        await LibraryService.update_extract_status(paper_id, "failed")
        raise HTTPException(500, detail=f"AI 提取失败: {str(e)}")


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
    """跨论文概念合并建议：找出在多篇论文中同名的概念"""
    if len(req.paper_ids) < 2:
        raise HTTPException(400, detail="至少选择 2 篇论文")

    import re
    from database import get_db

    def normalize(name: str) -> str:
        """规范化名称用于跨论文比对（去空白/连字符/引号，忽略大小写）"""
        return re.sub(r"[\s　\-_·.'\"()（）]+", "", name.lower())

    db = await get_db()

    # 收集各论文概念
    papers = []
    for pid in req.paper_ids:
        paper = await LibraryService.get_paper(pid)
        if not paper:
            continue
        rows = await db.execute_fetchall("SELECT * FROM concepts WHERE paper_id = ?", [pid])
        papers.append({"paper": paper, "concepts": [dict(r) for r in rows]})

    suggestions = []
    now = datetime.now().isoformat()

    # 两两论文比对同名概念
    for i in range(len(papers)):
        for j in range(i + 1, len(papers)):
            pa, pb = papers[i], papers[j]
            norm_map_b = {normalize(c["name"]): c for c in pb["concepts"]}
            for ca in pa["concepts"]:
                key = normalize(ca["name"])
                cb = norm_map_b.get(key)
                if not cb:
                    continue
                confidence = 0.95 if ca["name"] == cb["name"] else 0.7
                suggestions.append({
                    "conceptName": ca["name"],
                    "paperIdA": pa["paper"]["id"], "paperTitleA": pa["paper"]["title"], "slugA": ca["slug"],
                    "paperIdB": pb["paper"]["id"], "paperTitleB": pb["paper"]["title"], "slugB": cb["slug"],
                    "confidence": confidence,
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
    """全局概念搜索"""
    if not q:
        return R.success(data={"results": []})
    from database import get_db
    db = await get_db()
    rows = await db.execute_fetchall(
        """SELECT c.*, p.title as paper_title FROM concepts c
           JOIN papers p ON c.paper_id = p.id
           WHERE c.name LIKE ? OR c.definition LIKE ?
           LIMIT 30""",
        [f"%{q}%", f"%{q}%"]
    )
    type_colors = {"method": "#e8453c", "theory": "#8b5cf6", "dataset": "#10b981", "finding": "#f59e0b", "tool": "#00d4ff"}
    results = [{
        "id": r["slug"],
        "name": r["name"],
        "type": r["type"],
        "color": type_colors.get(r["type"], "#6b7280"),
        "paperTitle": r["paper_title"],
        "paperId": r["paper_id"],
    } for r in [dict(r) for r in rows]]
    return R.success(data={"results": results})


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


@router.post("/papers/{paper_id}/evidence-context")
async def evidence_context(paper_id: str, req: EvidenceContextRequest):
    """返回证据串在原文中的上下文与页码；无正文/找不到时 found=False"""
    from database import get_db
    db = await get_db()
    return R.success(data=await evidence_context_for_paper(db, paper_id, req.evidence))
