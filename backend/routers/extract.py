"""AI 提取接口 —— 提交/进度(SSE)/重试/文本/URL/空白论文创建"""

import asyncio
import ipaddress
import json
import os
import socket
import uuid
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import (
    EmptyPaperCreate,
    ExtractRequest,
    R,
    TextExtractRequest,
    UrlExtractRequest,
)
from services.extraction_service import extraction_manager
from services.library_service import LibraryService
from services.parser_registry import get_parser_for_paper

router = APIRouter(prefix="/api", tags=["extract"])

# URL 抓取防护：仅 http(s)、解析后拒绝私网/环回地址、响应体大小上限
_BLOCKED_NETWORKS = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "127.0.0.0/8", "169.254.0.0/16",
    "172.16.0.0/12", "192.168.0.0/16", "::1/128", "fc00::/7", "fe80::/10",
)]
_MAX_FETCH_BYTES = 5 * 1024 * 1024


def _validate_public_url(url: str) -> str:
    """SSRF 防护：仅允许 http/https，且域名解析结果全部为公网地址。

    已知边界：解析与实际请求之间存在 DNS rebinding 窗口（需自定义传输层才能彻底闭合）；
    本地单用户定位下该风险可接受，此处拦截的是最直接的私网探测。
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, detail="仅支持 http/https 链接")
    host = parsed.hostname
    if not host:
        raise HTTPException(400, detail="URL 缺少主机名")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise HTTPException(400, detail="无法解析主机名")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if any(ip in net for net in _BLOCKED_NETWORKS):
            raise HTTPException(400, detail="不允许访问内网/环回地址")
    return url


def _fetch_url_text(url: str) -> tuple[str, str]:
    """同步抓取网页并清洗出正文（供线程池调用，避免阻塞事件循环）"""
    resp = requests.get(url, timeout=15, headers={
        "User-Agent": "Mozilla/5.0 (compatible; WeaveKnowledge/3.1)"
    }, stream=True)
    resp.raise_for_status()
    # 截断到大小上限后再解码，防止超大页面撑爆内存
    raw = resp.raw.read(_MAX_FETCH_BYTES + 1, decode_content=True)[:_MAX_FETCH_BYTES]
    resp.encoding = resp.apparent_encoding or "utf-8"
    html = raw.decode(resp.encoding, errors="replace")

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return title, "\n".join(lines)[:80000]


# ── 提取任务（后台异步：SSE 实时进度 / 轮询降级 / 失败重试） ──

@router.post("/extract")
async def extract_knowledge(req: ExtractRequest):
    """对已上传的论文（PDF / DOCX）执行 AI 知识提取。

    提交后台任务后立即返回；进度经 SSE GET /extract/progress/{paper_id} 实时推送，
    或 GET /extract-status/{paper_id} 轮询查询。
    文本/URL 创建的论文（无 parser）若已有正文，同样可提交。
    """
    paper = await LibraryService.get_paper(req.paper_id)
    if paper is None:
        raise HTTPException(404, detail="论文不存在")
    parser = get_parser_for_paper(req.paper_id)
    if parser is not None and not os.path.exists(parser.get_path(req.paper_id)):
        raise HTTPException(404, detail="论文不存在")
    # 已完成且非空 → 幂等返回，不重复提取
    if paper["extract_status"] == "done" and paper["concept_count"] > 0:
        return R.success(data={"paperId": req.paper_id, "status": "done"})
    extraction_manager.submit(req.paper_id)
    return R.success(data={"paperId": req.paper_id, "status": "processing"})


@router.get("/extract-status/{paper_id}")
async def extract_status(paper_id: str):
    """查询论文提取任务状态：pending / processing / done / failed / not_found

    附带持久化的 stage/progress/detail/message/error（extract_tasks 表）。
    """
    return R.success(data=await extraction_manager.status(paper_id))


async def _progress_events(paper_id: str):
    """SSE 事件流：状态快照变化即推送，15s 心跳，终态后自动关闭（最长 20 分钟）"""
    last_payload = None
    idle = 0.0
    elapsed = 0.0
    while elapsed < 1200:
        snap = await extraction_manager.status(paper_id)
        if snap != last_payload:
            yield f"event: progress\ndata: {json.dumps(snap, ensure_ascii=False)}\n\n"
            last_payload = snap
            if snap["status"] in ("done", "failed", "not_found"):
                return
        await asyncio.sleep(0.5)
        idle += 0.5
        elapsed += 0.5
        if idle >= 15.0:
            yield ": keep-alive\n\n"
            idle = 0.0


@router.get("/extract/progress/{paper_id}")
async def extract_progress(paper_id: str):
    """SSE 实时提取进度：queued→parsing→extracting(i/n)→scoring→graphing→done/failed"""
    return StreamingResponse(
        _progress_events(paper_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/extract/{paper_id}/retry")
async def retry_extract(paper_id: str):
    """重试提取：重新提交后台任务（覆盖上次的任务记录与失败状态）"""
    paper = await LibraryService.get_paper(paper_id)
    if paper is None:
        raise HTTPException(404, detail="论文不存在")
    extraction_manager.retry(paper_id)
    return R.success(data={"paperId": paper_id, "status": "processing"})


# ── 知识入库入口 ──

@router.post("/extract-text")
async def extract_from_text(req: TextExtractRequest):
    """从粘贴的文本中提取知识（后台任务，立即返回 paperId）"""
    if not req.text.strip():
        raise HTTPException(400, detail="文本内容为空")

    paper_id = uuid.uuid4().hex[:12]
    await LibraryService.create_paper(
        paper_id=paper_id,
        title=req.title or "未命名知识",
        filename=f"{req.title or 'knowledge'}.txt",
        page_count=1,
        text_length=len(req.text),
    )
    await LibraryService.update_paper_text(paper_id, req.text)
    extraction_manager.submit(paper_id)
    return R.success(data={"paperId": paper_id, "status": "processing"})


@router.post("/extract-url")
async def extract_from_url(req: UrlExtractRequest):
    """从网页链接抓取文本并提取知识（SSRF 防护 + 响应体大小上限）"""
    if not req.url.strip():
        raise HTTPException(400, detail="URL 为空")

    url = _validate_public_url(req.url.strip())
    # 抓取网页（线程池执行：requests + BS4 解析均为同步阻塞调用）
    try:
        title, text = await asyncio.to_thread(_fetch_url_text, url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, detail=f"网页抓取失败: {str(e)}")

    paper_id = uuid.uuid4().hex[:12]
    await LibraryService.create_paper(
        paper_id=paper_id, title=title, filename=url,
        page_count=1, text_length=len(text),
    )
    await LibraryService.update_paper_text(paper_id, text)
    extraction_manager.submit(paper_id)
    return R.success(data={"paperId": paper_id, "status": "processing"})


@router.post("/papers/create-empty")
async def create_empty_paper(req: EmptyPaperCreate):
    """创建空白论文记录，用于手动构建知识"""
    paper_id = uuid.uuid4().hex[:12]
    await LibraryService.create_paper(
        paper_id=paper_id, title=req.title, filename="manual",
        page_count=0, text_length=0,
    )
    await LibraryService.update_extract_status(paper_id, "done", 0, 0)
    return R.success(data={"paper_id": paper_id, "title": req.title})
