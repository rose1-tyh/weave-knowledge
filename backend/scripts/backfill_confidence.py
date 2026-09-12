"""存量论文置信度回填 CLI：python -m scripts.backfill_confidence [paper_id]

不传 paper_id 则处理全部论文。演示前跑一次，让旧论文带上文本信号置信度。
"""
import asyncio
import sys

from database import close_db, get_db, init_db
from services.confidence_service import backfill_paper_confidences
from services.library_service import LibraryService
from services.parser_registry import get_parser_for_paper


async def main():
    paper_id = sys.argv[1] if len(sys.argv) > 1 else ""
    await init_db()
    db = await get_db()

    ids = [paper_id] if paper_id else \
        [r["id"] for r in await db.execute_fetchall("SELECT id FROM papers")]

    total_c = total_r = 0
    for pid in ids:
        t = await db.execute_fetchall("SELECT text FROM papers WHERE id = ?", [pid])
        if not t or not t[0]["text"]:
            parser = get_parser_for_paper(pid)
            if parser:
                try:
                    parsed = parser.extract(pid)
                    await LibraryService.update_paper_text(pid, parsed["full_text"])
                except Exception:
                    print(f"{pid}: 解析失败，跳过")
                    continue
        result = await backfill_paper_confidences(db, pid)
        total_c += result["concepts"]
        total_r += result["relations"]
        print(f"{pid}: {result['concepts']} 概念, {result['relations']} 关系")

    print(f"完成：{len(ids)} 篇，{total_c} 概念，{total_r} 关系")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
