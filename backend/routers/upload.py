"""PDF / DOCX 上传与解析接口"""

import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from models.schemas import R, PaperInfo
from services.pdf_service import PDFService
from services.docx_service import DocxService
from services.library_service import LibraryService

router = APIRouter(prefix="/api", tags=["upload"])


def _get_parser(filename: str):
    """按扩展名返回解析服务；不合法抛出 ValueError"""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return PDFService
    if ext == ".docx":
        return DocxService
    raise ValueError(f"不支持的文件类型: {ext}，仅允许 PDF / DOCX")


@router.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    """上传论文（PDF / DOCX），保存并提取文本，写入数据库"""
    if not file.filename:
        raise HTTPException(400, detail="文件名为空")
    try:
        parser = _get_parser(file.filename)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, detail="文件为空")
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, detail="文件超过 50MB 限制")

    paper_id = parser.save(content, file.filename)
    result = parser.extract(paper_id)

    # 写入数据库
    await LibraryService.create_paper(
        paper_id=paper_id,
        title=result["title"],
        filename=file.filename,
        page_count=result["page_count"],
        text_length=len(result["full_text"]),
    )

    return R.success(data=PaperInfo(
        paper_id=paper_id,
        title=result["title"],
        page_count=result["page_count"],
        text_length=len(result["full_text"]),
        text_preview=result["full_text"][:500],
    ).model_dump())


@router.get("/paper/{paper_id}")
async def get_paper_info(paper_id: str):
    """获取论文基本信息"""
    paper = await LibraryService.get_paper(paper_id)
    if not paper:
        raise HTTPException(404, detail="论文不存在")
    return R.success(data=paper)
