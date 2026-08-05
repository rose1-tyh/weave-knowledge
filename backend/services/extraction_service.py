"""提取任务管理服务 —— AI 提取后台异步执行，前端轮询状态

设计说明：
- 内存任务表（paper_id → asyncio.Task），适用于单进程 uvicorn 部署；
  多 worker 部署需外部队列（已知边界，见计划）。
- 任务状态以 papers.extract_status 为准（done/failed/processing），
  error 消息存内存表（进程重启后丢失，可接受）。
"""

import asyncio
import os

from services.library_service import LibraryService
from services.parser_registry import get_parser_for_paper
from services.graph_service import GraphService
from services.ai_service import AIService

ai_service = AIService()


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
    """后台提取任务注册表"""

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._errors: dict[str, str] = {}

    def submit(self, paper_id: str) -> bool:
        """提交提取任务；同论文已有运行中任务则不重复提交，返回 False"""
        task = self._tasks.get(paper_id)
        if task and not task.done():
            return False
        self._errors.pop(paper_id, None)
        self._tasks[paper_id] = asyncio.create_task(self._run(paper_id))
        return True

    async def status(self, paper_id: str) -> dict:
        """查询任务状态。

        运行中任务直接返回 processing（不查 DB，避免与任务写入竞态）；
        任务不存在或已完成 → 以 DB extract_status 为准（done/failed/pending/not_found），
        失败时附内存错误消息。
        """
        task = self._tasks.get(paper_id)
        if task is not None and not task.done():
            return {"status": "processing"}
        from database import get_db
        db = await get_db()
        rows = await db.execute_fetchall(
            "SELECT extract_status FROM papers WHERE id = ?", [paper_id])
        status = rows[0]["extract_status"] if rows else "not_found"
        result = {"status": status}
        if status == "failed" and paper_id in self._errors:
            result["error"] = self._errors[paper_id]
        return result

    async def _run(self, paper_id: str):
        """后台执行：取正文（DB 优先，无则解析文件）→ AI 提取 → 存库 → 状态流转"""
        try:
            from database import get_db
            db = await get_db()
            rows = await db.execute_fetchall(
                "SELECT title, text FROM papers WHERE id = ?", [paper_id])
            if not rows:
                return
            title = rows[0]["title"]
            text = rows[0]["text"]

            if not text:
                parser = get_parser_for_paper(paper_id)
                if parser is None or not os.path.exists(parser.get_path(paper_id)):
                    raise FileNotFoundError("论文不存在")
                parsed = parser.extract(paper_id)
                text = parsed["full_text"]
                await LibraryService.update_paper_text(paper_id, text)

            await LibraryService.update_extract_status(paper_id, "processing")

            raw = ai_service.extract_knowledge(text, title)
            graph = GraphService.build_graph(raw, title)

            if not graph.concepts:
                await LibraryService.update_extract_status(paper_id, "failed")
                self._errors[paper_id] = "未能提取到概念"
                return

            concepts_data = [c.model_dump() for c in graph.concepts]
            relations_data = _relations_with_slugs(graph)
            await LibraryService.save_concepts(paper_id, concepts_data)
            await LibraryService.save_relations(paper_id, relations_data)
            await LibraryService.update_extract_status(
                paper_id, "done", len(concepts_data), len(relations_data))
        except Exception as e:
            await LibraryService.update_extract_status(paper_id, "failed")
            self._errors[paper_id] = str(e)


# 全局单例（单进程 uvicorn）
extraction_manager = ExtractionManager()
