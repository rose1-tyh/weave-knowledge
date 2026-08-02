"""PDF 解析服务 —— PyMuPDF 文本提取"""

import os
import uuid
import fitz  # PyMuPDF
from config import PAPER_STORAGE_DIR, ALLOWED_EXTENSIONS


class PDFService:
    """PDF 文件处理：保存、文本提取、分页"""

    @staticmethod
    def validate(filename: str) -> str:
        """校验文件扩展名，返回小写扩展名；不合法抛出 ValueError"""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}，仅允许 PDF")
        return ext

    @staticmethod
    def save(file_bytes: bytes, filename: str) -> str:
        """保存 PDF 到本地存储，返回 paper_id"""
        paper_id = uuid.uuid4().hex[:12]
        save_path = os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.pdf")
        with open(save_path, "wb") as f:
            f.write(file_bytes)
        return paper_id

    @staticmethod
    def get_path(paper_id: str) -> str:
        return os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.pdf")

    @staticmethod
    def extract(paper_id: str) -> dict:
        """提取 PDF 全文，返回 { title, pages: [{num, text}], full_text, page_count }"""
        path = PDFService.get_path(paper_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f"论文不存在: {paper_id}")

        doc = fitz.open(path)
        meta = doc.metadata
        title = meta.get("title") or os.path.basename(path).replace(".pdf", "")

        pages = []
        full_parts = []
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            pages.append({"num": i + 1, "text": text})
            if text:
                full_parts.append(f"[第{i+1}页]\n{text}")

        doc.close()
        full_text = "\n\n".join(full_parts)
        return {
            "title": title,
            "pages": pages,
            "full_text": full_text,
            "page_count": len(pages),
        }
