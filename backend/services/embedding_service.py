"""可插拔 embedding 相似度服务 —— OpenAI 兼容 /embeddings 端点

DeepSeek/Anthropic 官方均无 embedding API，本服务面向第三方提供方
（如硅基流动 SiliconFlow、OpenAI 等兼容接口）。未配置 AI_EMBEDDING_*
时 similarity() 返回 None，调用方回退字符 bigram 相似度（零依赖运行）。
"""

import math
import requests
from config import AI_EMBEDDING_BASE_URL, AI_EMBEDDING_API_KEY, AI_EMBEDDING_MODEL


class EmbeddingService:
    """OpenAI 兼容 embedding 客户端；未配置时全部方法安全降级"""

    def __init__(self):
        self.base_url = AI_EMBEDDING_BASE_URL.rstrip("/")
        self.api_key = AI_EMBEDDING_API_KEY
        self.model = AI_EMBEDDING_MODEL

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key)

    def embed(self, text: str) -> list | None:
        """取文本向量；调用失败返回 None（不抛错，调用方回退）"""
        if not self.enabled or not text:
            return None
        try:
            resp = requests.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": text},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
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


# 全局单例
embedding_service = EmbeddingService()
