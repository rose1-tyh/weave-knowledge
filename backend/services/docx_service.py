"""DOCX 解析服务 —— python-docx 文本提取"""

import os
import uuid

from config import PAPER_STORAGE_DIR
from docx import Document


class DocxService:
    """DOCX 文件处理：保存、文本提取（docx 无分页，page_count 记为 1）"""

    @staticmethod
    def validate(filename: str) -> str:
        """校验文件扩展名，返回小写扩展名；不合法抛出 ValueError"""
        ext = os.path.splitext(filename)[1].lower()
        if ext != ".docx":
            raise ValueError(f"不支持的文件类型: {ext}，仅允许 PDF / DOCX")
        return ext

    @staticmethod
    def save(file_bytes: bytes, filename: str) -> str:
        """保存 DOCX 到本地存储，返回 paper_id"""
        paper_id = uuid.uuid4().hex[:12]
        save_path = os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.docx")
        with open(save_path, "wb") as f:
            f.write(file_bytes)
        return paper_id

    @staticmethod
    def get_path(paper_id: str) -> str:
        return os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.docx")

    @staticmethod
    def extract(paper_id: str) -> dict:
        """提取 DOCX 文本，返回 { title, pages, full_text, page_count }"""
        path = DocxService.get_path(paper_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f"论文不存在: {paper_id}")

        doc = Document(path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(paragraphs)

        return {
            "title": os.path.basename(path).replace(".docx", ""),
            "pages": [{"num": 1, "text": full_text}],
            "full_text": full_text,
            "page_count": 1,
        }
