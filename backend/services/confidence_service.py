"""置信度服务 —— AI 自评与文本信号交叉，产出可解释的最终置信度"""

import math
import re

LOW_CONFIDENCE_THRESHOLD = 0.6
OCCURRENCE_THRESHOLD = 3       # 出现 3 次以上视为文本信号封顶
KEY_SECTION_START = 0.10       # 开头 10% 视为摘要/引言
KEY_SECTION_END = 0.15         # 结尾 15% 视为结论


def _normalize(s: str) -> str:
    return re.sub(r"[\s　\-_·.'\"()（）]+", "", s.lower())


def _occurrence_count(name: str, text: str) -> int:
    needle = _normalize(name)
    if not needle:
        return 0
    return len(re.findall(re.escape(needle), _normalize(text)))


def text_signal_for_concept(name: str, text: str) -> float:
    """概念文本信号：出现次数 × 位置加权，0~1"""
    if not name or not text:
        return 0.0
    count = _occurrence_count(name, text)
    if count == 0:
        return 0.0
    n = len(text)
    idx = _normalize(text).find(_normalize(name))
    pos = 1.0 if idx >= 0 and (idx < n * KEY_SECTION_START or idx > n * (1 - KEY_SECTION_END)) else 0.0
    freq = min(1.0, count / OCCURRENCE_THRESHOLD)
    return round(freq * (0.7 + 0.3 * pos), 2)


def text_signal_for_relation(evidence: str, source_signal: float, target_signal: float, text: str) -> float:
    """关系文本信号：证据能否在全文定位（与证据服务一致的模糊匹配）× 两端概念信号均值"""
    from services.evidence_service import locate_evidence
    locatable = 1.0 if locate_evidence(text, evidence) else 0.0
    endpoints = (source_signal + target_signal) / 2.0
    return round(0.5 * locatable + 0.5 * endpoints, 2)


def final_confidence(ai_conf, text_signal: float) -> float:
    """最终置信度 = sqrt(ai × text_signal)；ai 缺失时退化为文本信号"""
    t = max(0.0, min(1.0, text_signal))
    if ai_conf is None:
        return round(t, 2)
    try:
        a = max(0.0, min(1.0, float(ai_conf)))
    except (TypeError, ValueError):
        a = 0.5
    return round(math.sqrt(a * t), 2)


def enrich(raw: dict, text: str) -> dict:
    """给 AI 原始输出补最终置信度字段，返回新 dict（不修改入参）"""
    concept_signals = {}
    new_concepts = []
    for c in raw.get("concepts", []):
        signal = text_signal_for_concept(c.get("name", ""), text)
        concept_signals[c.get("name", "")] = signal
        new_concepts.append({
            **c,
            "text_signal": signal,
            "confidence_ai": c.get("confidence"),
            "confidence": final_confidence(c.get("confidence"), signal),
        })
    new_relations = []
    for r in raw.get("relations", []):
        src = concept_signals.get(r.get("source", ""), 0.0)
        tgt = concept_signals.get(r.get("target", ""), 0.0)
        signal = text_signal_for_relation(r.get("evidence", ""), src, tgt, text)
        new_relations.append({
            **r,
            "text_signal": signal,
            "confidence_ai": r.get("confidence"),
            "confidence": final_confidence(r.get("confidence"), signal),
        })
    return {"concepts": new_concepts, "relations": new_relations}


async def backfill_paper_confidences(db, paper_id: str) -> dict:
    """重算一篇论文全部概念/关系的置信度（纯文本信号，confidence_ai 置 NULL）。

    供存量数据回填；无正文可算信号时跳过。
    """
    rows = await db.execute_fetchall("SELECT text FROM papers WHERE id = ?", [paper_id])
    text = rows[0]["text"] if rows else ""
    if not text:
        return {"concepts": 0, "relations": 0}

    concepts = [dict(r) for r in await db.execute_fetchall(
        "SELECT * FROM concepts WHERE paper_id = ?", [paper_id])]
    relations = [dict(r) for r in await db.execute_fetchall(
        "SELECT * FROM relations WHERE paper_id = ?", [paper_id])]

    signals = {}
    for c in concepts:
        s = text_signal_for_concept(c["name"], text)
        signals[c["slug"]] = s
        await db.execute(
            "UPDATE concepts SET confidence = ?, confidence_ai = NULL WHERE paper_id = ? AND slug = ?",
            [s, paper_id, c["slug"]])

    for r in relations:
        src = signals.get(r["source_slug"], 0.0)
        tgt = signals.get(r["target_slug"], 0.0)
        s = text_signal_for_relation(r["evidence"], src, tgt, text)
        await db.execute(
            "UPDATE relations SET confidence = ?, confidence_ai = NULL WHERE paper_id = ? AND id = ?",
            [s, paper_id, r["id"]])

    await db.commit()
    return {"concepts": len(concepts), "relations": len(relations)}
