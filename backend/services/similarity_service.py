"""概念相似度服务 —— 字符 bigram Jaccard（零依赖）+ 可插拔 embedding 精排

设计：DeepSeek/Anthropic 均无 embedding API，因此默认相似度为纯字符特征；
配置 AI_EMBEDDING_* 后由 embedding_service 提供余弦相似度加权（见 merge_suggestions）。
"""

import re

SIMILARITY_THRESHOLD = 0.6  # 建议合并的相似度阈值


def normalize(name: str) -> str:
    """规范化：去空白/连字符/引号/括号/点号，忽略大小写（与既有 merge 逻辑一致）"""
    return re.sub(r"[\s　\-_·.'\"()（）]+", "", name.lower())


def char_bigrams(s: str) -> set:
    """字符 bigram 集合（长度 <2 时退化为单字符集合）"""
    s = normalize(s)
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def char_bigram_jaccard(a: str, b: str) -> float:
    """字符 bigram 集合 Jaccard 相似度（0~1）"""
    ga, gb = char_bigrams(a), char_bigrams(b)
    if not ga or not gb:
        return 0.0
    union = len(ga | gb)
    if union == 0:
        return 0.0
    return len(ga & gb) / union


def concept_similarity(a: str, b: str, embedding_sim: float | None = None) -> float:
    """概念相似度：规范化后完全相等 → 1.0；否则 bigram Jaccard。

    embedding_sim 提供时加权（0.5 bigram + 0.5 embedding），缺省回退纯 bigram。
    """
    if normalize(a) == normalize(b):
        return 1.0
    bigram = char_bigram_jaccard(a, b)
    if embedding_sim is None:
        return round(bigram, 3)
    return round(0.5 * bigram + 0.5 * embedding_sim, 3)
