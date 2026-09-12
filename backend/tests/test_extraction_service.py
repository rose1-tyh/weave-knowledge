"""提取任务管理服务测试 —— 提交/幂等/状态流转/失败路径"""
import asyncio
import pytest
from services.extraction_service import ExtractionManager
from services.library_service import LibraryService


async def _seed_paper(db, pid="p1", with_text="论文正文"):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
        "VALUES (?, 't', 't.pdf', 1, 0, '2026-08-04', 'pending', ?)", [pid, with_text])
    await db.commit()


async def test_submit_creates_task_and_status(db, monkeypatch):
    """提交任务 → 状态机流转：pending → processing → done"""
    await _seed_paper(db)

    # 用假提取器替换 AI 调用，验证任务编排本身
    class FakeRaw:
        concepts = []
        relations = []
        title = "t"

    async def fake_run(self, paper_id):
        from services.library_service import LibraryService as LS
        await LS.update_extract_status(paper_id, "processing")
        await LS.update_extract_status(paper_id, "done", 0, 0)

    monkeypatch.setattr(ExtractionManager, "_run", fake_run)
    mgr = ExtractionManager()
    assert mgr.submit("p1") is True

    # 运行中重复提交 → 幂等 False（不重复创建任务）
    assert mgr.submit("p1") is False

    st = await mgr.status("p1")
    assert st["status"] in ("processing", "done")
    assert not st.get("error")

    # 等待后台任务收尾，避免 fixture 关闭连接时任务仍在访问
    await asyncio.gather(*mgr._tasks.values(), return_exceptions=True)


async def test_submit_after_done_restarts(db, monkeypatch):
    """任务完成后可再次提交（重新提取）"""
    await _seed_paper(db)
    await LibraryService.update_extract_status("p1", "done", 2, 1)

    async def fake_run(self, paper_id):
        await LibraryService.update_extract_status(paper_id, "processing")

    monkeypatch.setattr(ExtractionManager, "_run", fake_run)
    mgr = ExtractionManager()
    assert mgr.submit("p1") is True
    await asyncio.gather(*mgr._tasks.values(), return_exceptions=True)


async def test_status_not_found(db):
    mgr = ExtractionManager()
    st = await mgr.status("nope")
    assert st["status"] == "not_found"


async def test_run_success_flow_writes_db(db, monkeypatch):
    """真实 _run：解析正文（DB 已有 text）→ AI 提取 → 写库 → done"""
    await _seed_paper(db, with_text="图谱 图谱 图谱 图谱 图谱 图谱")

    fake_graph = {
        "concepts": [{
            "id": "abc12345", "name": "图谱", "definition": "d", "type": "finding",
            "page": 1, "evidence": "e", "confidence": 0.9, "confidence_ai": 0.9, "status": "pending",
        }],
        "relations": [],
    }
    from services import extraction_service as es

    async def fake_extract(self, text, title, on_progress=None):
        return fake_graph

    monkeypatch.setattr(es.AIService, "extract_knowledge", fake_extract)

    mgr = ExtractionManager()
    await mgr._run("p1")

    rows = await db.execute_fetchall("SELECT extract_status, concept_count FROM papers WHERE id = 'p1'")
    assert rows[0]["extract_status"] == "done"
    assert rows[0]["concept_count"] == 1
    # 概念落库
    c = await db.execute_fetchall("SELECT name FROM concepts WHERE paper_id = 'p1'")
    assert c[0]["name"] == "图谱"
    # 任务完成无错误
    st = await mgr.status("p1")
    assert st["status"] == "done"


async def test_run_failure_sets_failed(db, monkeypatch):
    """提取异常 → extract_status=failed + error 记录"""
    await _seed_paper(db)

    from services import extraction_service as es

    async def boom(self, text, title, on_progress=None):
        raise RuntimeError("AI 服务不可用")

    monkeypatch.setattr(es.AIService, "extract_knowledge", boom)
    mgr = ExtractionManager()
    await mgr._run("p1")

    rows = await db.execute_fetchall("SELECT extract_status FROM papers WHERE id = 'p1'")
    assert rows[0]["extract_status"] == "failed"
    st = await mgr.status("p1")
    assert st["status"] == "failed"
    assert "AI 服务不可用" in st["error"]


async def test_run_empty_concepts_sets_failed(db, monkeypatch):
    """AI 返回空概念 → failed + 明确错误"""
    await _seed_paper(db)

    from services import extraction_service as es

    async def fake_empty(self, text, title, on_progress=None):
        return {"concepts": [], "relations": []}

    monkeypatch.setattr(es.AIService, "extract_knowledge", fake_empty)

    mgr = ExtractionManager()
    await mgr._run("p1")
    rows = await db.execute_fetchall("SELECT extract_status FROM papers WHERE id = 'p1'")
    assert rows[0]["extract_status"] == "failed"
    assert "概念" in (await mgr.status("p1"))["error"]
