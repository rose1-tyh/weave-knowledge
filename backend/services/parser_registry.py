"""解析服务分发 —— 按文件名/存储物理文件选择 PDF / DOCX 解析器"""

import os

from config import PAPER_STORAGE_DIR

from services.docx_service import DocxService
from services.pdf_service import PDFService

pdf_service = PDFService()
docx_service = DocxService()


def get_parser_for_filename(filename: str):
    """按扩展名返回解析服务实例；不合法类型抛出 ValueError"""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return pdf_service
    if ext == ".docx":
        return docx_service
    raise ValueError(f"不支持的文件类型: {ext}，仅允许 PDF / DOCX")


def get_parser_for_paper(paper_id: str):
    """按物理文件选择解析服务；无文件返回 None"""
    if os.path.exists(os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.pdf")):
        return pdf_service
    if os.path.exists(os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.docx")):
        return docx_service
    return None
