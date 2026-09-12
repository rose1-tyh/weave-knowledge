"""可插拔 embedding 语义服务 —— OpenAI 兼容 /embeddings 端点 + 向量持久化

DeepSeek/Anthropic 官方均无 embedding API，本服务面向第三方提供方
（如硅基流动 SiliconFlow、OpenAI 等兼容接口）。未配置 AI_EMBEDDING_*
时全部方法安全降级（返回 None / 跳过索引），调用方回退字符 bigram 相似度。

向量持久化于 concept_embeddings 表（BLOB = float32 数组）：
- 提取完成后异步建立概念向量索引（extraction_service 触发）
- 混合检索语义通道读取向量做余弦召回（search_service）
- 跨论文 merge 建议复用已存向量，避免请求时逐对实时调 HTTP
"""

import array
import asyncio
import math

import requests
from config import AI_EMBEDDING_API_KEY, AI_EMBEDDING_BASE_URL, AI_EMBEDDING_MODEL

# 语义召回的余弦相似度门槛（cosine 已归一化到 0~1）
SEMANTIC_THRESHOLD = 0.55


def pack_vector(vec: list) -> bytes:
    """float 列表 → float32 BLOB（存储格式）"""
    return array.array("f", vec).tobytes()


def unpack_vector(blob: bytes) -> list:
    """float32 BLOB → float 列表"""
    a = array.array("f")
    a.frombytes(blob)
    return a.tolist()


class EmbeddingService:
    """OpenAI 兼容 embedding 客户端；未配置时全部方法安全降级"""

    def __init__(self):
        self.base_url = AI_EMBEDDING_BASE_URL.rstrip("/")
        self.api_key = AI_EMBEDDING_API_KEY
        self.model = AI_EMBEDDING_MODEL

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _post_embeddings(self, texts: list[str]) -> list[list]:
        """同步批量调用 /embeddings（供线程池执行）"""
        resp = requests.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]

    async def embed_batch(self, texts: list[str]) -> list[list] | None:
        """批量向量化；未配置或调用失败返回 None（不抛错，调用方回退）"""
        if not self.enabled or not texts:
            return None
        try:
            return await asyncio.to_thread(self._post_embeddings, list(texts))
        except Exception:
            return None

    async def embed_query(self, text: str) -> list | None:
        """查询向量（检索语义通道入口）"""
        if not text:
            return None
        vectors = await self.embed_batch([text])
        return vectors[0] if vectors else None

    def embed(self, text: str) -> list | None:
        """取文本向量（同步单条；兼容旧调用方）；调用失败返回 None"""
        if not self.enabled or not text:
            return None
        try:
            return self._post_embeddings([text])[0]
        except Exception:
            return None

    @staticmethod
    def cosine(va: list, vb: list) -> float:
        """余弦相似度（0~1 归一化处理负向量）"""
        if not va or not vb or len(va) != len(vb):
            return 0.0
        dot = sum(x * y for x, y in zip(va, vb))
        na = math.sqrt(sum(x * x for x in va))
        nb = math.sqrt(sum(x * x for x in vb))
        if na == 0 or nb == 0:
            return 0.0
        return max(0.0, min(1.0, (dot / (na * nb) + 1) / 2))

    def similarity(self, a: str, b: str) -> float | None:
        """两文本语义相似度；未配置或调用失败返回 None"""
        if not self.enabled:
            return None
        va, vb = self.embed(a), self.embed(b)
        if va is None or vb is None:
            return None
        return round(self.cosine(va, vb), 3)

    # ── 向量持久化 ──

    async def index_concepts(self, rows: list[dict]) -> int:
        """批量建立概念向量索引。

        rows: [{paper_id, slug, name, definition}]；
        文本 = name + definition；未配置 embedding 或调用失败时静默跳过（返回 0）。
        """
        if not self.enabled or not rows:
            return 0
        vectors = await self.embed_batch([f"{r['name']} {r['definition']}".strip() for r in rows])
        if vectors is None:
            return 0
        from datetime import datetime

        from database import get_db
        db = await get_db()
        now = datetime.now().isoformat()
        count = 0
        for r, vec in zip(rows, vectors):
            if not vec:
                continue
            await db.execute(
                "INSERT OR REPLACE INTO concept_embeddings (paper_id, slug, model, dim, vector, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [r["paper_id"], r["slug"], self.model, len(vec), pack_vector(vec), now],
            )
            count += 1
        await db.commit()
        return count

    async def index_paper_concepts(self, paper_id: str, concepts: list[dict]) -> int:
        """提取完成后的论文概念索引入口（concepts_data: [{id, name, definition}]）"""
        rows = [{"paper_id": paper_id, "slug": c["id"], "name": c["name"],
                 "definition": c.get("definition", "")} for c in concepts]
        return await self.index_concepts(rows)

    async def load_vectors(self, paper_ids: list[str] | None = None) -> dict:
        """读取向量索引：{(paper_id, slug): vector}；可按论文过滤"""
        from database import get_db
        db = await get_db()
        if paper_ids:
            placeholders = ",".join("?" * len(paper_ids))
            rows = await db.execute_fetchall(
                f"SELECT paper_id, slug, vector FROM concept_embeddings WHERE paper_id IN ({placeholders})",
                list(paper_ids))
        else:
            rows = await db.execute_fetchall("SELECT paper_id, slug, vector FROM concept_embeddings")
        return {(r["paper_id"], r["slug"]): unpack_vector(r["vector"]) for r in rows}


# 全局单例
embedding_service = EmbeddingService()
