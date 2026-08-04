"""Pydantic 数据模型"""

from pydantic import BaseModel
from typing import Optional, List, Literal


# ── 统一响应 ──

class R(BaseModel):
    code: int = 200
    msg: str = "操作成功"
    data: Optional[object] = None

    @staticmethod
    def success(data=None, msg="操作成功"):
        return R(code=200, msg=msg, data=data)

    @staticmethod
    def error(msg="操作失败", code=500):
        return R(code=code, msg=msg, data=None)


# ── 论文 ──

class PaperInfo(BaseModel):
    paper_id: str
    title: str
    page_count: int
    text_length: int
    text_preview: str = ""

class PaperUpdate(BaseModel):
    title: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None

# ── 知识提取 ──

class ExtractRequest(BaseModel):
    paper_id: str

class ConceptCreate(BaseModel):
    name: str
    definition: str = ""
    type: str = "finding"
    page: int = 1

class ConceptUpdate(BaseModel):
    name: Optional[str] = None
    definition: Optional[str] = None
    type: Optional[str] = None
    page: Optional[int] = None
    status: Optional[Literal["pending", "confirmed", "rejected"]] = None

class RelationCreate(BaseModel):
    source_slug: str
    target_slug: str
    type: str = "cites"
    evidence: str = ""

class RelationUpdate(BaseModel):
    type: Optional[str] = None
    evidence: Optional[str] = None
    status: Optional[Literal["pending", "confirmed", "rejected"]] = None

class EvidenceContextRequest(BaseModel):
    evidence: str

# ── 文本/URL 提取 ──

class TextExtractRequest(BaseModel):
    title: str
    text: str

class UrlExtractRequest(BaseModel):
    url: str

# ── 全局探索 ──

class FusionRequest(BaseModel):
    paper_ids: List[str]

class MergeSuggestRequest(BaseModel):
    paper_ids: List[str]
