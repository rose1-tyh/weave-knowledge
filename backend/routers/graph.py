"""图谱接口 —— 图谱数据、概念/关系 CRUD（带存在性校验）、证据上下文、导出"""

import hashlib
from datetime import datetime

from fastapi import APIRouter, HTTPException
from models.schemas import (
    ConceptCreate,
    ConceptUpdate,
    EvidenceContextRequest,
    R,
    RelationCreate,
    RelationUpdate,
)
from services.evidence_service import evidence_context_for_paper
from services.export_service import ExportService
from services.library_service import LibraryService

router = APIRouter(prefix="/api", tags=["graph"])


# ── 图谱数据 ──

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
    """手动添加概念（slug 冲突返回 409）"""
    paper = await LibraryService.get_paper(paper_id)
    if paper is None:
        raise HTTPException(404, detail="论文不存在")
    slug = hashlib.md5(req.name.encode()).hexdigest()[:8]
    now = datetime.now().isoformat()
    from database import get_db
    db = await get_db()
    exists = await db.execute_fetchall(
        "SELECT 1 FROM concepts WHERE paper_id = ? AND slug = ?", [paper_id, slug])
    if exists:
        raise HTTPException(409, detail="同名概念已存在")
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
    cursor = await db.execute(
        f"UPDATE concepts SET {', '.join(updates)} WHERE paper_id = ? AND slug = ?",
        params
    )
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, detail="概念不存在")
    return R.success()


@router.delete("/graph/{paper_id}/concepts/{slug}")
async def delete_concept(paper_id: str, slug: str):
    """删除概念（级联删除关联关系）"""
    from database import get_db
    db = await get_db()
    exists = await db.execute_fetchall(
        "SELECT 1 FROM concepts WHERE paper_id = ? AND slug = ?", [paper_id, slug])
    if not exists:
        raise HTTPException(404, detail="概念不存在")
    await db.execute(
        "DELETE FROM relations WHERE paper_id = ? AND (source_slug = ? OR target_slug = ?)",
        [paper_id, slug, slug])
    await db.execute("DELETE FROM concepts WHERE paper_id = ? AND slug = ?", [paper_id, slug])
    await db.commit()
    return R.success()


# ── 关系 CRUD ──

@router.post("/graph/{paper_id}/relations")
async def create_relation(paper_id: str, req: RelationCreate):
    """手动添加关系（两端概念必须存在）"""
    from database import get_db
    db = await get_db()
    for field, val in (("source", req.source_slug), ("target", req.target_slug)):
        exists = await db.execute_fetchall(
            "SELECT 1 FROM concepts WHERE paper_id = ? AND slug = ?", [paper_id, val])
        if not exists:
            raise HTTPException(400, detail=f"{field} 概念不存在")
    now = datetime.now().isoformat()
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
        updates.append("type = ?")
        params.append(req.type)
    if req.evidence is not None:
        updates.append("evidence = ?")
        params.append(req.evidence)
    if req.status is not None:
        updates.append("status = ?")
        params.append(req.status)
    if not updates:
        return R.success()
    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.extend([paper_id, rel_id])
    cursor = await db.execute(
        f"UPDATE relations SET {', '.join(updates)} WHERE paper_id = ? AND id = ?", params)
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, detail="关系不存在")
    return R.success()


@router.delete("/graph/{paper_id}/relations/{rel_id}")
async def delete_relation(paper_id: str, rel_id: int):
    """删除关系"""
    from database import get_db
    db = await get_db()
    cursor = await db.execute("DELETE FROM relations WHERE paper_id = ? AND id = ?", [paper_id, rel_id])
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, detail="关系不存在")
    return R.success()


# ── 证据上下文 ──

@router.post("/papers/{paper_id}/evidence-context")
async def evidence_context(paper_id: str, req: EvidenceContextRequest):
    """返回证据串在原文中的上下文与页码；无正文/找不到时 found=False"""
    from database import get_db
    db = await get_db()
    return R.success(data=await evidence_context_for_paper(db, paper_id, req.evidence))


# ── 导出 ──

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
