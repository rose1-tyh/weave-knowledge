"""混合检索服务 —— FTS5 关键词通道 + embedding 语义通道 + RRF 融合排序

三个召回通道：
- concepts：概念全文索引（BM25 排名，命中名/定义）
- fulltext：论文正文全文索引（BM25 排名，snippet 高亮）
- semantic：查询向量 × concept_embeddings 余弦召回（未配置 embedding 自动跳过）

融合采用 Reciprocal Rank Fusion（RRF）：score = Σ channel_weight / (k + rank)，
k=60 为经验值（与前作 TREC 一致），对异构通道的分数量纲不敏感。
"""

import re

from services.embedding_service import embedding_service, SEMANTIC_THRESHOLD

RRF_K = 60
CHANNEL_LIMIT = 50          # 每通道参与融合的最大候选数
TYPE_COLORS = {"method": "#e8453c", "theory": "#8b5cf6", "dataset": "#10b981",
               "finding": "#f59e0b", "tool": "#00d4ff"}


def rrf_fuse(channels: dict[str, list[tuple]], weights: dict[str, float] | None = None) -> dict:
    """RRF 融合。

    channels: {通道名: [(key, metadata), ...]}，列表按通道内相关性降序；
    返回 {key: {"score": rrf分, "channels": [命中通道...], "meta": 首个命中的元数据}}
    """
    weights = weights or {}
    fused: dict = {}
    for channel, ranked in channels.items():
        w = weights.get(channel, 1.0)
        for rank, (key, meta) in enumerate(ranked):
            entry = fused.setdefault(key, {"score": 0.0, "channels": [], "meta": meta})
            entry["score"] += w / (RRF_K + rank + 1)
            if channel not in entry["channels"]:
                entry["channels"].append(channel)
    return fused


def sanitize_query(q: str) -> str:
    """FTS5 短语查询净化：剥离 MATCH 语法字符（引号/星号/括号/冒号/空白）"""
    return re.sub(r'["*():\s]+', "", q)


class SearchService:
    """混合检索：关键词（概念/正文）+ 语义三通道 RRF 融合，分页输出"""

    async def search(self, q: str, scope: str = "all", page: int = 1, size: int = 20) -> dict:
        q = (q or "").strip()
        if not q:
            return {"results": [], "total": 0, "page": page, "size": size, "channels": {}}
        scope = scope if scope in ("all", "concepts", "fulltext") else "all"

        channels: dict[str, list[tuple]] = {}
        if scope in ("all", "concepts"):
            channels["concepts"] = await self._concept_channel(q)
        if scope in ("all", "fulltext"):
            channels["fulltext"] = await self._fulltext_channel(q)
        if scope in ("all", "concepts"):
            channels["semantic"] = await self._semantic_channel(q)

        channel_counts = {k: len(v) for k, v in channels.items() if v}
        fused = rrf_fuse(channels)
        ranked = sorted(fused.items(), key=lambda kv: kv[1]["score"], reverse=True)

        total = len(ranked)
        offset = (page - 1) * size
        results = [self._format(key, entry) for key, entry in ranked[offset:offset + size]]
        return {"results": results, "total": total, "page": page, "size": size,
                "channels": channel_counts}

    # ── 召回通道 ──

    async def _concept_channel(self, q: str) -> list[tuple]:
        """概念通道：≥3 字符 FTS5 短语（BM25），否则 LIKE 回退"""
        from database import get_db
        db = await get_db()
        clean = sanitize_query(q)
        if len(clean) >= 3:
            rows = await db.execute_fetchall(
                """SELECT c.slug, c.name, c.type, c.definition, c.paper_id, p.title AS paper_title
                   FROM concepts_fts f
                   JOIN concepts c ON c.id = f.rowid
                   JOIN papers p ON c.paper_id = p.id
                   WHERE concepts_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                [f'"{clean}"', CHANNEL_LIMIT])
        else:
            rows = await db.execute_fetchall(
                """SELECT c.slug, c.name, c.type, c.definition, c.paper_id, p.title AS paper_title
                   FROM concepts c JOIN papers p ON c.paper_id = p.id
                   WHERE c.name LIKE ? OR c.definition LIKE ?
                   LIMIT ?""",
                [f"%{q}%", f"%{q}%", CHANNEL_LIMIT])
        return [(("concept", r["paper_id"], r["slug"]), dict(r)) for r in rows]

    async def _fulltext_channel(self, q: str) -> list[tuple]:
        """正文通道：论文标题+正文 FTS，snippet() 生成高亮片段"""
        from database import get_db
        db = await get_db()
        clean = sanitize_query(q)
        if len(clean) >= 3:
            rows = await db.execute_fetchall(
                """SELECT p.id AS paper_id, p.title, p.text_length,
                          snippet(papers_fts, 1, '<mark>', '</mark>', '…', 24) AS snip
                   FROM papers_fts f
                   JOIN papers p ON p.rowid = f.rowid
                   WHERE papers_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                [f'"{clean}"', CHANNEL_LIMIT])
        else:
            rows = await db.execute_fetchall(
                """SELECT id AS paper_id, title, text_length, '' AS snip
                   FROM papers
                   WHERE title LIKE ? OR text LIKE ?
                   LIMIT ?""",
                [f"%{q}%", f"%{q}%", CHANNEL_LIMIT])
        return [(("paper", r["paper_id"]), dict(r)) for r in rows]

    async def _semantic_channel(self, q: str) -> list[tuple]:
        """语义通道：查询向量与概念向量余弦召回；未配置 embedding 返回空"""
        if not embedding_service.enabled:
            return []
        query_vec = await embedding_service.embed_query(q)
        if not query_vec:
            return []
        vectors = await embedding_service.load_vectors()
        if not vectors:
            return []
        scored = []
        for (paper_id, slug), vec in vectors.items():
            if len(vec) != len(query_vec):
                continue
            sim = embedding_service.cosine(query_vec, vec)
            if sim >= SEMANTIC_THRESHOLD:
                scored.append((sim, paper_id, slug))
        scored.sort(reverse=True)
        scored = scored[:CHANNEL_LIMIT]
        if not scored:
            return []

        from database import get_db
        db = await get_db()
        meta_rows = await db.execute_fetchall(
            """SELECT c.slug, c.name, c.type, c.definition, c.paper_id, p.title AS paper_title
               FROM concepts c JOIN papers p ON c.paper_id = p.id
               WHERE c.slug || '|' || c.paper_id IN (%s)""" %
            ",".join("?" * len(scored)),
            [f"{slug}|{pid}" for _, pid, slug in scored])
        meta = {(r["paper_id"], r["slug"]): dict(r) for r in meta_rows}
        ranked = []
        for sim, paper_id, slug in scored:
            m = meta.get((paper_id, slug))
            if m:
                m["semantic_score"] = round(sim, 4)
                ranked.append((("concept", paper_id, slug), m))
        return ranked

    # ── 输出格式 ──

    def _format(self, key: tuple, entry: dict) -> dict:
        kind = key[0]
        meta = entry["meta"]
        if kind == "concept":
            return {
                "kind": "concept",
                "id": meta["slug"],
                "name": meta["name"],
                "type": meta["type"],
                "color": TYPE_COLORS.get(meta["type"], "#6b7280"),
                "snippet": meta.get("definition", "")[:160],
                "paperId": meta["paper_id"],
                "paperTitle": meta.get("paper_title", ""),
                "channels": entry["channels"],
                "score": round(entry["score"], 6),
            }
        return {
            "kind": "paper",
            "id": meta["paper_id"],
            "title": meta["title"],
            "snippet": meta.get("snip", ""),
            "textLength": meta.get("text_length", 0),
            "channels": entry["channels"],
            "score": round(entry["score"], 6),
        }


# 全局单例
search_service = SearchService()
