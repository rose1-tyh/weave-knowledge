"""解析服务分发 —— 按存储物理文件选择 PDF / DOCX 解析器"""

import os
from config import PAPER_STORAGE_DIR
from services.pdf_service import PDFService
from services.docx_service import DocxService

pdf_service = PDFService()
docx_service = DocxService()


def get_parser_for_paper(paper_id: str):
    """按物理文件选择解析服务；无文件返回 None"""
    if os.path.exists(os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.pdf")):
        return pdf_service
    if os.path.exists(os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.docx")):
        return docx_service
    return None
