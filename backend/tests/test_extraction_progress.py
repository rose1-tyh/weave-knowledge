"""提取进度持久化 + 重试 + SSE 进度流 + 事件循环响应性测试"""
import asyncio
import json
import time

from services.extraction_service import ExtractionManager
from services.library_service import LibraryService


def _concept(name="概念A"):
    return {"id": "abc12345", "name": name, "definition": "d", "type": "finding",
            "page": 1, "evidence": "e", "confidence": 0.9, "confidence_ai": 0.9,
            "status": "pending"}


async def _seed_paper(db, pid="p1", with_text="论文正文"):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
        "VALUES (?, 't', 't.pdf', 1, 0, '2026-08-04', 'pending', ?)", [pid, with_text])
    await db.commit()


async def test_progress_stages_recorded(db, monkeypatch):
    """分阶段进度写入 extract_tasks：运行中可读，终态 progress=1.0"""
    await _seed_paper(db, "p-prog")
    from services import extraction_service as es

    async def fake_extract(self, text, title, on_progress=None):
        await on_progress("extracting", 0.3, "1/1")
        # 回调写入后立即可查（真实进度而非事后补写）
        row = await db.execute_fetchall(
            "SELECT stage, progress, detail FROM extract_tasks WHERE paper_id = 'p-prog'")
        assert row[0]["stage"] == "extracting"
        assert row[0]["progress"] == 0.3
        assert row[0]["detail"] == "1/1"
        return {"concepts": [_concept()], "relations": []}

    monkeypatch.setattr(es.AIService, "extract_knowledge", fake_extract)
    mgr = ExtractionManager()
    await mgr._run("p-prog")

    row = await db.execute_fetchall(
        "SELECT stage, progress, message FROM extract_tasks WHERE paper_id = 'p-prog'")
    assert row[0]["stage"] == "done"
    assert row[0]["progress"] == 1.0
    assert "提取完成" in row[0]["message"]
    paper = await LibraryService.get_paper("p-prog")
    assert paper["extract_status"] == "done"
    assert paper["concept_count"] == 1


async def test_status_maps_stage_to_status(db, monkeypatch):
    """任务行 stage → status 映射：非终态 = processing，终态 = done/failed"""
    await _seed_paper(db, "p-map")
    mgr = ExtractionManager()
    from database import get_db
    conn = await get_db()
    await conn.execute(
        "INSERT INTO extract_tasks (paper_id, stage, progress, updated_at) "
        "VALUES ('p-map', 'extracting', 0.5, '2026-01-01')")
    await conn.commit()
    st = await mgr.status("p-map")
    assert st["status"] == "processing"
    assert st["stage"] == "extracting"


async def test_retry_after_failure(db, monkeypatch):
    """失败后重试：重新提交并覆盖任务记录，二次成功 → done"""
    await _seed_paper(db, "p-retry")
    from services import extraction_service as es
    calls = {"n": 0}

    async def flaky(self, text, title, on_progress=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("网络抖动")
        return {"concepts": [_concept()], "relations": []}

    monkeypatch.setattr(es.AIService, "extract_knowledge", flaky)
    mgr = ExtractionManager()
    await mgr._run("p-retry")
    assert (await mgr.status("p-retry"))["status"] == "failed"
    assert "网络抖动" in (await mgr.status("p-retry"))["error"]

    assert mgr.retry("p-retry") is True
    await asyncio.gather(*mgr._tasks.values())
    st = await mgr.status("p-retry")
    assert st["status"] == "done"
    assert calls["n"] == 2


async def test_retry_rejected_while_running(db, monkeypatch):
    """运行中重试被拒绝"""
    await _seed_paper(db, "p-run")
    from services import extraction_service as es

    async def slow(self, text, title, on_progress=None):
        await asyncio.sleep(0.2)
        return {"concepts": [_concept()], "relations": []}

    monkeypatch.setattr(es.AIService, "extract_knowledge", slow)
    mgr = ExtractionManager()
    mgr.submit("p-run")
    assert mgr.retry("p-run") is False
    await asyncio.gather(*mgr._tasks.values())


async def test_recover_stale_marks_failed(db):
    """启动恢复：遗留运行中任务 → failed（可重试）"""
    await _seed_paper(db, "p-stale")
    await db.execute(
        "INSERT INTO extract_tasks (paper_id, stage, progress, updated_at) "
        "VALUES ('p-stale', 'extracting', 0.5, '2026-01-01')")
    await db.execute("UPDATE papers SET extract_status='processing' WHERE id='p-stale'")
    await db.commit()

    mgr = ExtractionManager()
    await mgr.recover_stale()
    st = await mgr.status("p-stale")
    assert st["status"] == "failed"
    assert "重启" in st["error"]


async def test_sse_stream_snapshots_and_closes(db, monkeypatch):
    """SSE 事件流：先推快照，终态推送后自动关闭"""
    await _seed_paper(db, "p-sse")
    from services import extraction_service as es

    async def fake_extract(self, text, title, on_progress=None):
        await asyncio.sleep(0.6)  # 给首帧快照留出时间
        return {"concepts": [_concept()], "relations": []}

    monkeypatch.setattr(es.AIService, "extract_knowledge", fake_extract)
    mgr = ExtractionManager()
    assert mgr.submit("p-sse") is True

    from routers.extract import _progress_events
    events = []
    async for chunk in _progress_events("p-sse"):
        events.append(chunk)
    # 走到这里说明流已自动关闭（终态退出）
    assert any('"processing"' in e for e in events)
    done_lines = [e for e in events if '"done"' in e and e.startswith("event: progress")]
    assert done_lines, "缺少终态 done 事件"
    payload = json.loads(done_lines[-1].split("data: ", 1)[1])
    assert payload["status"] == "done"
    assert payload["progress"] == 1.0


async def test_llm_call_runs_in_thread_pool(db, monkeypatch):
    """LLM 同步阻塞调用经线程池执行：阻塞期间事件循环持续调度其他协程"""
    from services import extraction_service as es

    def slow_llm(self, chunk, label):
        time.sleep(0.3)
        return {"concepts": [{"name": "概念A", "definition": "", "type": "finding",
                              "page": 1, "evidence": "", "confidence": 0.9}],
                "relations": []}

    monkeypatch.setattr(es.AIService, "_extract_single", slow_llm)

    ticks = {"n": 0}
    stop = {"flag": False}

    async def ticker():
        while not stop["flag"]:
            ticks["n"] += 1
            await asyncio.sleep(0.02)

    t = asyncio.create_task(ticker())
    result = await es.ai_service.extract_knowledge("短文本", "t")
    stop["flag"] = True
    await t

    assert result["concepts"][0]["name"] == "概念A"
    # 若阻塞调用跑在事件循环上，ticks 将接近 0；线程池执行则持续 ≥5
    assert ticks["n"] >= 5, f"事件循环被阻塞（ticks={ticks['n']}）"


def test_progress_and_retry_routes_registered():
    from main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/extract/progress/{paper_id}" in paths
    assert "/api/extract/{paper_id}/retry" in paths
