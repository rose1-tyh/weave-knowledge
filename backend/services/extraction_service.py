"""提取任务管理服务 —— AI 提取后台异步执行 + 任务持久化 + 分阶段真实进度

设计说明：
- 任务状态持久化于 extract_tasks 表（stage/progress/error），进程重启不丢、可重试；
  内存 _tasks 仅用于运行中去重（单进程 uvicorn 部署边界不变）。
- 进度阶段：queued → parsing → chunking → extracting(i/n) → scoring → graphing → done/failed，
  各阶段映射到 0-1 总进度；前端经 SSE GET /api/extract/progress/{paper_id} 实时获取，
  GET /api/extract-status/{paper_id} 轮询作为降级兜底。
- AI 调用与文档解析均经 asyncio.to_thread 执行，提取期间事件循环保持响应。
"""

import asyncio
import os
from datetime import datetime

from services.ai_service import AIService
from services.embedding_service import EmbeddingService
from services.graph_service import GraphService
from services.library_service import LibraryService
from services.parser_registry import get_parser_for_paper
from services.settings_service import SettingsService

# 阶段 → 总进度锚点（extracting 为区间，按分片数在区间内线性推进）
STAGE_PROGRESS = {
    "queued": 0.0,
    "parsing": 0.08,
    "chunking": 0.15,
    "extracting": (0.2, 0.85),
    "scoring": 0.9,
    "graphing": 0.96,
    "done": 1.0,
}


def _relations_with_slugs(graph) -> list[dict]:
    """把 AI 提取的关系中的概念名重映射为 slug，保证与手动关系存储一致"""
    name_to_slug = {c.name: c.id for c in graph.concepts}
    result = []
    for r in graph.relations:
        rd = r.model_dump()
        rd["source"] = name_to_slug.get(rd["source"], rd["source"])
        rd["target"] = name_to_slug.get(rd["target"], rd["target"])
        result.append(rd)
    return result


class ExtractionManager:
    """后台提取任务注册表（状态持久化于 extract_tasks 表）"""

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._bg: set[asyncio.Task] = set()  # 后台衍生任务强引用，防 GC

    def _spawn_bg(self, coro):
        """衍生后台任务（如向量索引），失败不影响主流程"""
        task = asyncio.create_task(coro)
        self._bg.add(task)
        task.add_done_callback(self._bg.discard)

    # ── 任务状态持久化 ──

    async def _record(self, paper_id: str, stage: str, progress: float | None = None,
                      detail: str = "", message: str = "", error: str = ""):
        """写入/更新任务行（每篇论文保留最新一次任务）"""
        from database import get_db
        db = await get_db()
        if progress is None:
            anchor = STAGE_PROGRESS.get(stage)
            progress = anchor if isinstance(anchor, (int, float)) else 0.0
        now = datetime.now().isoformat()
        await db.execute(
            "INSERT INTO extract_tasks (paper_id, stage, progress, detail, message, error, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(paper_id) DO UPDATE SET stage=excluded.stage, progress=excluded.progress, "
            "detail=excluded.detail, message=excluded.message, error=excluded.error, updated_at=excluded.updated_at",
            [paper_id, stage, round(float(progress), 4), detail, message, error, now],
        )
        await db.commit()

    async def recover_stale(self):
        """服务启动时清理上次进程遗留的运行中任务 → 标记失败（前端可重试）"""
        from database import get_db
        db = await get_db()
        rows = await db.execute_fetchall(
            "SELECT paper_id FROM extract_tasks WHERE stage NOT IN ('done', 'failed')")
        for r in rows:
            await self._record(r["paper_id"], "failed", error="服务重启导致任务中断，可重试")
        await db.execute("UPDATE papers SET extract_status='failed' WHERE extract_status='processing'")
        await db.commit()

    # ── 任务生命周期 ──

    def submit(self, paper_id: str) -> bool:
        """提交提取任务；同论文已有运行中任务则不重复提交，返回 False"""
        if self.running(paper_id):
            return False
        self._tasks[paper_id] = asyncio.create_task(self._run(paper_id))
        return True

    def running(self, paper_id: str) -> bool:
        task = self._tasks.get(paper_id)
        return task is not None and not task.done()

    def retry(self, paper_id: str) -> bool:
        """重试提取：重新提交任务（任务行与论文状态由 _run 覆盖）；运行中则拒绝"""
        if self.running(paper_id):
            return False
        self.submit(paper_id)
        return True

    async def status(self, paper_id: str) -> dict:
        """查询任务状态。优先级：本进程运行中任务（立即 processing）→
        extract_tasks 记录（stage→status 映射）→ papers.extract_status 回退（历史数据/手动建库）。"""
        from database import get_db
        db = await get_db()
        paper_rows = await db.execute_fetchall(
            "SELECT extract_status FROM papers WHERE id = ?", [paper_id])
        if not paper_rows:
            return {"status": "not_found", "stage": "", "progress": 0.0,
                    "detail": "", "message": "", "error": ""}
        rows = await db.execute_fetchall(
            "SELECT stage, progress, detail, message, error FROM extract_tasks WHERE paper_id = ?",
            [paper_id])
        if rows and rows[0]["stage"] in ("done", "failed"):
            t = rows[0]
            return {"status": t["stage"], "stage": t["stage"], "progress": t["progress"],
                    "detail": t["detail"], "message": t["message"], "error": t["error"]}
        if self.running(paper_id):
            if rows:
                t = rows[0]
                return {"status": "processing", "stage": t["stage"], "progress": t["progress"],
                        "detail": t["detail"], "message": t["message"], "error": t["error"]}
            # submit 与首帧写库之间的窗口：立即确认 processing，避免调用方误判 pending
            return {"status": "processing", "stage": "queued", "progress": 0.0,
                    "detail": "", "message": "任务已排队", "error": ""}
        if rows:
            t = rows[0]
            return {"status": "processing", "stage": t["stage"], "progress": t["progress"],
                    "detail": t["detail"], "message": t["message"], "error": t["error"]}
        ps = paper_rows[0]["extract_status"]
        return {"status": ps, "stage": "", "progress": 1.0 if ps == "done" else 0.0,
                "detail": "", "message": "", "error": ""}

    # ── 执行管线 ──

    async def _run(self, paper_id: str):
        """后台执行：排队 → 取正文（DB 优先，无则线程池解析文件）→ AI 提取（分片进度回调）
        → 置信度交叉 → 建图 → 存库 → 状态流转"""
        try:
            await self._record(paper_id, "queued", message="任务已排队")
            from database import get_db
            db = await get_db()
            rows = await db.execute_fetchall(
                "SELECT title, text FROM papers WHERE id = ?", [paper_id])
            if not rows:
                await self._record(paper_id, "failed", error="论文不存在")
                return
            title = rows[0]["title"]
            text = rows[0]["text"]

            if not text:
                await self._record(paper_id, "parsing", message="解析文档")
                parser = get_parser_for_paper(paper_id)
                if parser is None or not os.path.exists(parser.get_path(paper_id)):
                    raise FileNotFoundError("论文不存在")
                parsed = await asyncio.to_thread(parser.extract, paper_id)
                text = parsed["full_text"]
                await LibraryService.update_paper_text(paper_id, text)

            await LibraryService.update_extract_status(paper_id, "processing")

            async def on_progress(stage: str, progress: float, detail: str):
                await self._record(paper_id, stage, progress=progress,
                                   detail=detail, message=f"AI 提取中（{detail}）")

            # BYOK：每次任务读当前用户设置（改 Key 立即生效，无需重启）
            settings = await SettingsService.get_all()
            svc = AIService.for_settings(settings)
            raw = await svc.extract_knowledge(text, title, on_progress=on_progress)

            await self._record(paper_id, "scoring", message="置信度交叉评估")
            graph = GraphService.build_graph(raw, title)

            await self._record(paper_id, "graphing", message="构建知识图谱")
            if not graph.concepts:
                await LibraryService.update_extract_status(paper_id, "failed")
                await self._record(paper_id, "failed", error="未能提取到概念")
                return

            concepts_data = [c.model_dump() for c in graph.concepts]
            relations_data = _relations_with_slugs(graph)
            await LibraryService.save_concepts(paper_id, concepts_data)
            await LibraryService.save_relations(paper_id, relations_data)
            await LibraryService.update_extract_status(
                paper_id, "done", len(concepts_data), len(relations_data))
            await self._record(paper_id, "done",
                               message=f"提取完成：{len(concepts_data)} 个概念 · {len(relations_data)} 条关系")
            # 语义向量索引（best-effort：未配置 embedding 时内部跳过；失败不回滚提取结果）
            emb = EmbeddingService.for_settings(settings)
            self._spawn_bg(emb.index_paper_concepts(paper_id, concepts_data))
        except Exception as e:
            await LibraryService.update_extract_status(paper_id, "failed")
            await self._record(paper_id, "failed", error=str(e))


# 全局单例（单进程 uvicorn）
extraction_manager = ExtractionManager()
