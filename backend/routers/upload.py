"""PDF / DOCX 上传与解析接口"""

from config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, MAX_FILE_SIZE_MB
from fastapi import APIRouter, File, HTTPException, UploadFile
from models.schemas import PaperInfo, R
from services.library_service import LibraryService
from services.parser_registry import get_parser_for_filename

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    """上传论文（PDF / DOCX），保存并提取文本，写入数据库"""
    if not file.filename:
        raise HTTPException(400, detail="文件名为空")
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, detail=f"不支持的文件类型: {ext}，仅允许 PDF / DOCX")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, detail="文件为空")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, detail=f"文件超过 {MAX_FILE_SIZE_MB}MB 限制")

    try:
        parser = get_parser_for_filename(file.filename)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

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
