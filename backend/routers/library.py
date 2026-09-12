"""知识库接口 —— 论文列表/详情/更新/删除、仪表盘统计、知识分析"""

from fastapi import APIRouter, HTTPException
from models.schemas import PaperUpdate, R
from services.library_service import LibraryService

router = APIRouter(prefix="/api", tags=["library"])


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
async def update_paper(paper_id: str, req: PaperUpdate):
    """更新论文信息（title/tags/notes）"""
    paper = await LibraryService.get_paper(paper_id)
    if not paper:
        raise HTTPException(404, detail="论文不存在")
    data = req.model_dump(exclude_none=True)
    if data:
        await LibraryService.update_paper(paper_id, data)
    return R.success()


@router.delete("/library/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """删除论文及关联数据"""
    paper = await LibraryService.get_paper(paper_id)
    if not paper:
        raise HTTPException(404, detail="论文不存在")
    await LibraryService.delete_paper(paper_id)
    return R.success()


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
