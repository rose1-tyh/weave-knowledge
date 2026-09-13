"""系统接口 —— 存量数据回填、向量索引重建"""

from fastapi import APIRouter
from models.schemas import R
from services.library_service import LibraryService
from services.parser_registry import get_parser_for_paper

router = APIRouter(prefix="/api", tags=["system"])


@router.post("/system/backfill-confidence")
async def backfill_confidence(paper_id: str = ""):
    """存量论文置信度回填（纯文本信号）；指定 paper_id 则只处理该篇"""
    from database import get_db
    from services.confidence_service import backfill_paper_confidences
    db = await get_db()
    if paper_id:
        ids = [paper_id]
    else:
        rows = await db.execute_fetchall("SELECT id FROM papers")
        ids = [r["id"] for r in rows]

    total_c = total_r = 0
    processed = 0
    for pid in ids:
        # 无正文且可解析的论文：补正文
        t = await db.execute_fetchall("SELECT text FROM papers WHERE id = ?", [pid])
        if not t or not t[0]["text"]:
            parser = get_parser_for_paper(pid)
            if parser:
                try:
                    parsed = parser.extract(pid)
                    await LibraryService.update_paper_text(pid, parsed["full_text"])
                except Exception:
                    continue
        result = await backfill_paper_confidences(db, pid)
        total_c += result["concepts"]
        total_r += result["relations"]
        processed += 1
    return R.success(data={"processed": processed, "concepts": total_c, "relations": total_r})


@router.post("/system/reindex-embeddings")
async def reindex_embeddings():
    """全库重建概念向量索引（语义检索数据源）；未配置 embedding 时 skipped=True"""
    from database import get_db
    from services.embedding_service import EmbeddingService
    from services.settings_service import SettingsService
    emb = EmbeddingService.for_settings(await SettingsService.get_all())
    if not emb.enabled:
        return R.success(data={"indexed": 0, "skipped": True})
    db = await get_db()
    rows = await db.execute_fetchall("SELECT paper_id, slug, name, definition FROM concepts")
    indexed = await emb.index_concepts([dict(r) for r in rows])
    return R.success(data={"indexed": indexed})
