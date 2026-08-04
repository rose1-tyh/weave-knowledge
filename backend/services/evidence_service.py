"""证据定位服务 —— 在论文正文中定位证据串，返回上下文与页码"""

import re

PAGE_MARKER_RE = re.compile(r"\[第(\d+)页\]\n?")


def _fuzzy_pattern(evidence: str) -> re.Pattern | None:
    """宽松匹配：逐字符，字符间允许任意空白（忽略证据内的空白差异）"""
    parts = []
    for ch in evidence:
        if ch.isspace():
            continue
        parts.append(re.escape(ch) + r"\s*")
    if not parts:
        return None
    return re.compile("".join(parts), re.IGNORECASE)


def locate_evidence(text: str, evidence: str, context_chars: int = 150) -> dict | None:
    """在正文中定位证据串。

    context 为证据前后各 context_chars 字符；start/end 是证据在 context 内的下标；
    page 由证据前最近的 [第N页] 标记推断。找不到返回 None。
    """
    if not text or not evidence:
        return None
    idx = text.find(evidence)
    if idx >= 0:
        m_start, m_end = idx, idx + len(evidence)
    else:
        pattern = _fuzzy_pattern(evidence)
        if pattern is None:
            return None
        m = pattern.search(text)
        if not m:
            return None
        m_start, m_end = m.start(), m.end()

    s = max(0, m_start - context_chars)
    e = min(len(text), m_end + context_chars)

    markers = PAGE_MARKER_RE.findall(text[:m_start])
    page = int(markers[-1]) if markers else 1

    return {
        "context": text[s:e],
        "start": m_start - s,
        "end": m_end - s,
        "page": page,
    }


async def evidence_context_for_paper(db, paper_id: str, evidence: str) -> dict:
    """从论文正文取证据上下文；无正文或找不到时返回 {found: False}"""
    rows = await db.execute_fetchall("SELECT text FROM papers WHERE id = ?", [paper_id])
    if not rows or not rows[0]["text"]:
        return {"found": False, "reason": "原文不可用"}
    loc = locate_evidence(rows[0]["text"], evidence)
    if not loc:
        return {"found": False, "reason": "未找到证据串"}
    return {"found": True, **loc}
