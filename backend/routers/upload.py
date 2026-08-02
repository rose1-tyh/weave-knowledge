"""PDF 上传与解析接口"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from models.schemas import R, PaperInfo
from services.pdf_service import PDFService
from services.library_service import LibraryService

router = APIRouter(prefix="/api", tags=["upload"])
pdf_service = PDFService()


@router.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    """上传论文 PDF，保存并提取文本，写入数据库"""
    if not file.filename:
        raise HTTPException(400, detail="文件名为空")
    try:
        pdf_service.validate(file.filename)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, detail="文件为空")
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, detail="文件超过 50MB 限制")

    paper_id = pdf_service.save(content, file.filename)
    result = pdf_service.extract(paper_id)

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
