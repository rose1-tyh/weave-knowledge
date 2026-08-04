# 可信抽取 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给织识的概念与关系增加证据页码、原文片段、置信度（AI自评×文本信号交叉）与人工确认状态，前端以印章/虚线呈现并支持证据弹窗跳转。

**Architecture:** 后端优先。SQLite 幂等迁移加列 → 纯函数置信度/证据定位服务（可独立测试）→ AI prompt 升级 + 容错解析 → 持久化透传 + 论文正文入库 → 新端点 → 前端图谱状态渲染与侧栏确认交互。最终置信度用 `sqrt(ai × text_signal)` 几何平均，AI 自评分缺失时退化为纯文本信号。

**Tech Stack:** Python FastAPI + aiosqlite(SQLite) + pytest/pytest-asyncio；Vue3 + Pinia + D3 + Vitest + @vue/test-utils。

## Global Constraints

- 数据库 `backend/storage/weave.db`（SQLite，无迁移框架）：所有 `ALTER TABLE` 必须幂等（`PRAGMA table_info` 检查后仅加缺失列）。
- 正文带页码标记：`pdf_service.extract` 返回的 `full_text` 形如 `"[第N页]\n<文本>"`（用 `\n\n` 连接）。证据页码从证据前最近的 `[第N页]` 标记推断，**不依赖** AI 报告的 page。
- AI 输出容错：`confidence` 缺失 → 默认 0.5；越界 → clamp [0,1]；概念 `evidence` 缺失 → 默认空串；`page` 无法解析 → 默认 1。
- 置信度公式：概念文本信号 `min(1.0, 出现次数/3) × (0.7 + 0.3×位置加权)`；关系文本信号 `0.5×证据可定位 + 0.5×(两端概念信号均值)`；最终 `sqrt(ai × text_signal)`，ai 为 None 时用 `text_signal`。全部 clamp 到 [0,1] 并 round 到 2 位小数。
- 状态枚举：`pending` / `confirmed` / `rejected`（rejected 仅标记，保留在图上）。
- 低置信阈值：`< 0.6`（`LOW_CONFIDENCE_THRESHOLD`）。
- 前端节点新字段：`confidence / confidence_ai / status / evidence`；连线新字段：`confidence / confidence_ai / status / page`。
- 中文 UI 文案；提交信息用 Conventional Commits。

---

### Task 1: 测试基础设施 + Schema 幂等迁移

**Files:**
- Create: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_schema_migration.py`
- Modify: `backend/database.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: 无
- Produces:
  - `database.migrate_schema(db)` — async，接受 aiosqlite 连接，幂等补列；`init_db()` 在建表后调用
  - `backend/tests/conftest.py` 的 `db` fixture — async，临时 SQLite 连接 + 已建表
  - pytest 运行方式：`cd backend && python -m pytest`（pytest-asyncio 自动模式）

- [ ] **Step 1: 加 pytest 依赖**

`backend/requirements.txt` 末尾追加：
```
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: 建 pytest 配置**

Create `backend/pytest.ini`：
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 3: 写迁移测试（先红）**

Create `backend/tests/conftest.py`：
```python
import aiosqlite
import pytest
import database


@pytest.fixture
async def db(tmp_path):
    """临时 SQLite 连接，跑 init_db 建表；测试间隔离"""
    conn = await aiosqlite.connect(tmp_path / "test.db")
    conn.row_factory = aiosqlite.Row
    database.DB = conn
    await database.init_db()
    yield conn
    await conn.close()
    database.DB = None
```

Create `backend/tests/test_schema_migration.py`：
```python
import database


async def test_migrate_schema_is_idempotent(db):
    await database.migrate_schema(db)
    await database.migrate_schema(db)  # 第二次不应报错、不重复加列

    cols = {r["name"] for r in await db.execute_fetchall("PRAGMA table_info(concepts)")}
    assert {"evidence", "confidence", "confidence_ai", "status"} <= cols

    cols = {r["name"] for r in await db.execute_fetchall("PRAGMA table_info(relations)")}
    assert {"confidence", "confidence_ai", "status", "page"} <= cols

    cols = {r["name"] for r in await db.execute_fetchall("PRAGMA table_info(papers)")}
    assert "text" in cols


async def test_migrate_preserves_existing_rows(db):
    now = "2026-08-04T00:00:00"
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
        "VALUES ('p1', '测试', 't.pdf', 1, 10, ?, 'done')", [now])
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES ('p1', 'abc', '概念A', '定义', 'finding', 1, 'ai', ?, ?)", [now, now])
    await db.commit()

    await database.migrate_schema(db)

    rows = await db.execute_fetchall("SELECT * FROM concepts WHERE slug='abc'")
    assert len(rows) == 1
    assert rows[0]["name"] == "概念A"
    assert rows[0]["confidence"] == 0.5   # 默认值
    assert rows[0]["status"] == "pending"
```

- [ ] **Step 4: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_schema_migration.py -v`
Expected: FAIL — `AttributeError: module 'database' has no attribute 'migrate_schema'`

- [ ] **Step 5: 实现迁移**

Modify `backend/database.py`：在 `init_db` 的 `executescript` 块之后、`await db.commit()` 之前调用迁移，并新增：
```python
# 幂等迁移：表名 → 需补充的列定义（SQLite 无 IF NOT EXISTS for ADD COLUMN）
MIGRATIONS = {
    "papers": ["text TEXT DEFAULT ''"],
    "concepts": [
        "evidence TEXT DEFAULT ''",
        "confidence REAL DEFAULT 0.5",
        "confidence_ai REAL",
        "status TEXT DEFAULT 'pending'",
    ],
    "relations": [
        "confidence REAL DEFAULT 0.5",
        "confidence_ai REAL",
        "status TEXT DEFAULT 'pending'",
        "page INTEGER",
    ],
}


async def migrate_schema(db):
    """幂等迁移：对缺失列执行 ALTER TABLE ADD COLUMN"""
    for table, columns in MIGRATIONS.items():
        rows = await db.execute_fetchall(f"PRAGMA table_info({table})")
        existing = {r["name"] for r in rows}
        for col in columns:
            col_name = col.split(" ")[0]
            if col_name not in existing:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
    await db.commit()
```

`init_db()` 末尾改为：
```python
    await db.executescript(""" ... 原建表脚本 ... """)
    await migrate_schema(db)
    await db.commit()
```

- [ ] **Step 6: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_schema_migration.py -v`
Expected: PASS（2 passed）

- [ ] **Step 7: Commit**

```bash
git add backend/pytest.ini backend/tests/ backend/database.py backend/requirements.txt
git commit -m "test(backend): 迁移基础设施 + 可信抽取字段幂等迁移"
```

---

### Task 2: 置信度服务（纯函数）

**Files:**
- Create: `backend/services/confidence_service.py`
- Create: `backend/tests/test_confidence_service.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `text_signal_for_concept(name: str, text: str) -> float`
  - `text_signal_for_relation(evidence: str, source_signal: float, target_signal: float, text: str) -> float`
  - `final_confidence(ai_conf: float | None, text_signal: float) -> float`
  - `enrich(raw: dict, text: str) -> dict` — 为概念/关系补 `confidence`(最终)、`confidence_ai`(AI原始)、`text_signal` 字段，返回新 dict（不改入参）
  - 常量 `LOW_CONFIDENCE_THRESHOLD = 0.6`

- [ ] **Step 1: 写测试（先红）**

Create `backend/tests/test_confidence_service.py`：
```python
import pytest
from services.confidence_service import (
    text_signal_for_concept, text_signal_for_relation, final_confidence, enrich,
)


def test_concept_signal_zero_when_absent():
    assert text_signal_for_concept("图谱", "本文主要讨论文本分析。") == 0.0


def test_concept_signal_saturates_with_frequency():
    text = "图谱 图谱 图谱 图谱 图谱 图谱"
    assert text_signal_for_concept("图谱", text) == pytest.approx(1.0, abs=0.01)


def test_concept_signal_position_bonus():
    # 概念在摘要/结论位置出现 → 信号高于只在正文中部出现
    key = "图谱 概念定义。\n\n" + ("正文内容。" * 100) + "\n\n图谱 结论。"
    mid = "正文内容。" * 50 + "图谱 图谱" + "正文内容。" * 50
    assert text_signal_for_concept("图谱", key) > text_signal_for_concept("图谱", mid)


def test_relation_signal_uses_evidence_locatability():
    text = "图谱 图谱 图谱 图谱 图谱 图谱"
    found = text_signal_for_relation("图谱 图谱", 1.0, 1.0, text)
    missing = text_signal_for_relation("不存在的证据串", 1.0, 1.0, text)
    assert found > missing


def test_final_confidence_geometric_mean():
    assert final_confidence(0.9, 0.4) == pytest.approx(0.6, abs=0.01)


def test_final_confidence_clamps():
    assert final_confidence(1.5, 0.5) <= 1.0
    assert final_confidence(-0.2, 0.5) >= 0.0


def test_final_confidence_falls_back_to_text_signal():
    assert final_confidence(None, 0.7) == pytest.approx(0.7, abs=0.01)


def test_enrich_adds_fields_and_preserves_input():
    raw = {
        "concepts": [{"name": "图谱", "definition": "d", "type": "finding", "page": 1, "confidence": 0.9}],
        "relations": [{"source": "图谱", "target": "文本", "type": "cites", "evidence": "x", "confidence": 0.8}],
    }
    original = raw["concepts"][0]["confidence"]
    out = enrich(raw, "图谱 图谱 图谱 文本 文本 文本")
    assert out["concepts"][0]["confidence_ai"] == 0.9
    assert out["concepts"][0]["confidence"] <= 0.9
    assert "text_signal" in out["concepts"][0]
    assert out["relations"][0]["confidence_ai"] == 0.8
    assert "text_signal" in out["relations"][0]
    assert raw["concepts"][0]["confidence"] == original  # 入参不被修改
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_confidence_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.confidence_service'`

- [ ] **Step 3: 实现服务**

Create `backend/services/confidence_service.py`：
```python
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
    """关系文本信号：证据能否在全文定位 × 两端概念信号均值"""
    locatable = 1.0 if evidence and evidence.strip() and evidence.strip() in text else 0.5
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_confidence_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/confidence_service.py backend/tests/test_confidence_service.py
git commit -m "feat(confidence): AI×文本信号交叉置信度纯函数服务"
```

---

### Task 3: 证据定位服务（纯函数）

**Files:**
- Create: `backend/services/evidence_service.py`
- Create: `backend/tests/test_evidence_service.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `locate_evidence(text: str, evidence: str, context_chars: int = 150) -> dict | None` — 返回 `{context, start, end, page}`；找不到返回 None
  - `evidence_context_for_paper(db, paper_id: str, evidence: str) -> dict` — 读 `papers.text`，返回 `{found, reason?, context?, start?, end?, page?}`

- [ ] **Step 1: 写测试（先红）**

Create `backend/tests/test_evidence_service.py`：
```python
from services.evidence_service import locate_evidence, evidence_context_for_paper

TEXT = "[第1页]\n引言 本文介绍图谱。\n\n[第2页]\n图谱是知识结构。证据在这里出现。\n\n[第3页]\n结论。"


def test_locate_exact():
    loc = locate_evidence(TEXT, "图谱是知识结构")
    assert loc is not None
    assert loc["page"] == 2
    assert 0 <= loc["start"] < loc["end"] <= len(loc["context"])
    assert "图谱是知识结构" in loc["context"][loc["start"]:loc["end"]]


def test_locate_not_found():
    assert locate_evidence(TEXT, "完全不存在的概念") is None


def test_locate_empty_input():
    assert locate_evidence(TEXT, "") is None
    assert locate_evidence("", "x") is None


def test_locate_whitespace_tolerant():
    loc = locate_evidence(TEXT, "图谱是  知识 结构")
    assert loc is not None
    assert loc["page"] == 2


async def test_evidence_context_found(db):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
        "VALUES ('p1','t','t.pdf',1,0,'2026-08-04','done','[第1页]\\n图谱是知识结构。')")
    await db.commit()
    result = await evidence_context_for_paper(db, "p1", "图谱是知识结构")
    assert result["found"] is True
    assert result["page"] == 1


async def test_evidence_context_missing_text(db):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
        "VALUES ('p1','t','t.pdf',1,0,'2026-08-04','done')")
    await db.commit()
    result = await evidence_context_for_paper(db, "p1", "x")
    assert result["found"] is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_evidence_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.evidence_service'`

- [ ] **Step 3: 实现服务**

Create `backend/services/evidence_service.py`：
```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_evidence_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/evidence_service.py backend/tests/test_evidence_service.py
git commit -m "feat(evidence): 原文证据定位服务——上下文+页码推断"
```

---

### Task 4: AI prompt 升级 + 容错解析 + graph_service 透传

**Files:**
- Modify: `backend/services/ai_service.py`
- Modify: `backend/services/graph_service.py`
- Create: `backend/tests/test_parse_robustness.py`

**Interfaces:**
- Consumes: `confidence_service.enrich(raw, text)`（Task 2）
- Produces:
  - `ai_service.extract_knowledge` 返回的 raw 已含每个概念的 `confidence`(最终)/`confidence_ai`/`text_signal`/`evidence`，每个关系的 `confidence`/`confidence_ai`/`text_signal`/`page`
  - `AIService._sanitize_result(raw) -> dict` — 归一化 + 默认值 + clamp
  - `graph_service.ConceptData` 含 `evidence/confidence/confidence_ai/status`；`RelationData` 含 `confidence/confidence_ai/status/page`；`build_graph`/`to_d3_format`/`model_dump` 透传

- [ ] **Step 1: 写测试（先红）**

Create `backend/tests/test_parse_robustness.py`：
```python
from services.ai_service import AIService


def test_sanitize_missing_confidence_defaults_to_05():
    raw = {"concepts": [{"name": "概念", "definition": "d", "type": "finding", "page": 2}],
           "relations": [{"source": "概念", "target": "其他", "type": "cites", "evidence": "e"}]}
    out = AIService._sanitize_result(raw)
    assert out["concepts"][0]["confidence"] == 0.5
    assert out["concepts"][0]["evidence"] == ""
    assert out["relations"][0]["confidence"] == 0.5


def test_sanitize_clamps_out_of_range():
    raw = {"concepts": [{"name": "c", "confidence": 1.5}], "relations": []}
    assert AIService._sanitize_result(raw)["concepts"][0]["confidence"] == 1.0


def test_sanitize_handles_garbage_page():
    raw = {"concepts": [{"name": "c", "page": "abc"}], "relations": []}
    assert AIService._sanitize_result(raw)["concepts"][0]["page"] == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_parse_robustness.py -v`
Expected: FAIL — `AttributeError: type object 'AIService' has no attribute '_sanitize_result'`

- [ ] **Step 3: 升级 prompt**

Modify `backend/services/ai_service.py` 的 `KNOWLEDGE_EXTRACTION_PROMPT`，任务描述改为：
```
1. **提取核心概念**（5-10个）：每个概念包含：
   - name: 概念名称（简洁，2-8字）
   - definition: 一句话定义（清晰阐述该概念在论文中的含义）
   - type: 概念类型，从以下选择：method（研究方法）、theory（理论基础）、dataset（数据集）、finding（研究发现）、tool（工具/系统）
   - page: 该概念在原文中首次出现或核心论述所在的页码
   - evidence: 原文中最能定义该概念的一句话（直接引用原文，不要改写）
   - confidence: 0-1 的数值，表示你对该概念真实存在于论文且有价值的把握程度

2. **提取概念间关系**：
   - source: 源概念名称（必须与上面提取的 name 完全一致）
   - target: 目标概念名称（必须与上面提取的 name 完全一致）
   - type: 关系类型，从以下选择：supports（A支撑/验证B）、contradicts（A与B矛盾/质疑）、extends（A扩展/改进B）、cites（A引用B）、uses（A使用B作为方法/工具）
   - evidence: 原文中体现该关系的具体语句（直接引用）
   - page: 该关系证据所在页码
   - confidence: 0-1 的数值，表示你对该关系真实存在的把握程度
```

输出格式示例同步更新：
```
{
  "concepts": [
    {"name": "...", "definition": "...", "type": "...", "page": 1, "evidence": "...", "confidence": 0.9}
  ],
  "relations": [
    {"source": "...", "target": "...", "type": "...", "evidence": "...", "page": 1, "confidence": 0.8}
  ]
}
```

- [ ] **Step 4: 实现容错解析 + 交叉接入**

Modify `backend/services/ai_service.py`：
- 顶部导入：`from services.confidence_service import enrich`
- `AIService` 新增两个静态方法：
```python
    @staticmethod
    def _clamp01(v):
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return 0.5

    @staticmethod
    def _safe_int(v, default):
        try:
            return int(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _sanitize_result(raw: dict) -> dict:
        """归一化 AI 输出：缺字段补默认值、越界 clamp、类型矫正"""
        concepts = []
        for c in raw.get("concepts", []):
            concepts.append({
                "name": str(c.get("name", "")),
                "definition": str(c.get("definition", "")),
                "type": str(c.get("type", "finding")),
                "page": AIService._safe_int(c.get("page"), 1),
                "evidence": str(c.get("evidence", "")),
                "confidence": AIService._clamp01(c.get("confidence")),
            })
        relations = []
        for r in raw.get("relations", []):
            relations.append({
                "source": str(r.get("source", "")),
                "target": str(r.get("target", "")),
                "type": str(r.get("type", "cites")),
                "evidence": str(r.get("evidence", "")),
                "page": AIService._safe_int(r.get("page"), None),
                "confidence": AIService._clamp01(r.get("confidence")),
            })
        return {"concepts": concepts, "relations": relations}
```
- 重构 `extract_knowledge`，让容错 + 交叉都发生在合并结果之后：
```python
    def extract_knowledge(self, full_text: str, paper_title: str) -> dict:
        if len(full_text) <= MAX_CHUNK_CHARS:
            raw = self._extract_single(full_text, paper_title)
        else:
            raw = self._extract_chunked(full_text, paper_title)
        sanitized = self._sanitize_result(raw)
        return enrich(sanitized, full_text)
```
- 把原 `extract_knowledge` 中分片合并的逻辑抽为私有方法 `_extract_chunked(self, full_text, paper_title) -> dict`，返回合并去重后的 raw（原 `_extract_single` 不变）。合并规则：`full_text` 超 `MAX_CHUNK_CHARS` 时按段落边界切分（沿用现 `_chunk_text`），对每段调用 `_extract_single`；概念按 `name` 去重（首次出现保留），关系按 `(source, target, type)` 去重。

- [ ] **Step 5: 升级 graph_service 透传**

Modify `backend/services/graph_service.py`：

`ConceptData.__init__` 签名与字段改为：
```python
    def __init__(self, id, name, definition, type, page,
                 evidence="", confidence=0.5, confidence_ai=None, status="pending"):
        self.id = id
        self.name = name
        self.definition = definition
        self.type = type
        self.page = page
        self.evidence = evidence
        self.confidence = confidence
        self.confidence_ai = confidence_ai
        self.status = status

    def model_dump(self) -> dict:
        return {"id": self.id, "name": self.name, "definition": self.definition,
                "type": self.type, "page": self.page, "evidence": self.evidence,
                "confidence": self.confidence, "confidence_ai": self.confidence_ai,
                "status": self.status}
```

`RelationData.__init__` 签名与字段改为：
```python
    def __init__(self, source, target, type, evidence,
                 confidence=0.5, confidence_ai=None, status="pending", page=None):
        self.source = source
        self.target = target
        self.type = type
        self.evidence = evidence
        self.confidence = confidence
        self.confidence_ai = confidence_ai
        self.status = status
        self.page = page

    def model_dump(self) -> dict:
        return {"source": self.source, "target": self.target, "type": self.type,
                "evidence": self.evidence, "confidence": self.confidence,
                "confidence_ai": self.confidence_ai, "status": self.status, "page": self.page}
```

`build_graph` 概念构造改为：
```python
            concepts.append(ConceptData(
                id=slug,
                name=c.get("name", ""),
                definition=c.get("definition", ""),
                type=c.get("type", "finding"),
                page=c.get("page", 1),
                evidence=c.get("evidence", ""),
                confidence=c.get("confidence", 0.5),
                confidence_ai=c.get("confidence_ai"),
                status=c.get("status", "pending"),
            ))
```
关系构造改为：
```python
                relations.append(RelationData(
                    source=src,
                    target=tgt,
                    type=r.get("type", "cites"),
                    evidence=r.get("evidence", ""),
                    confidence=r.get("confidence", 0.5),
                    confidence_ai=r.get("confidence_ai"),
                    status=r.get("status", "pending"),
                    page=r.get("page"),
                ))
```

`to_d3_format` 节点追加 `"evidence": c.evidence, "confidence": c.confidence, "confidence_ai": c.confidence_ai, "status": c.status`；连线追加 `"confidence": r.confidence, "confidence_ai": r.confidence_ai, "status": r.status, "page": r.page`。

- [ ] **Step 6: 跑全部后端测试确认通过**

Run: `cd backend && python -m pytest -v`
Expected: PASS（迁移 2 + 置信度 8 + 证据 5 + 容错 3）

- [ ] **Step 7: Commit**

```bash
git add backend/services/ai_service.py backend/services/graph_service.py backend/tests/test_parse_robustness.py
git commit -m "feat(ai): 抽取 prompt 加证据/置信度 + 容错解析 + 图谱透传"
```

---

### Task 5: 持久化透传 + 论文正文入库 + 解析分发抽取

**Files:**
- Modify: `backend/services/library_service.py`
- Modify: `backend/routers/knowledge.py`
- Create: `backend/services/parser_registry.py`
- Create: `backend/tests/test_library_service.py`

**Interfaces:**
- Consumes: 新字段；`get_db()`；pdf/docx 解析服务
- Produces:
  - `services.parser_registry.get_parser_for_paper(paper_id) -> parser | None` — 按存储物理文件分发 PDF/DOCX 解析器
  - `LibraryService.save_concepts` 写 `evidence/confidence/confidence_ai/status`
  - `LibraryService.save_relations` 写 `confidence/confidence_ai/status/page`
  - `LibraryService.update_paper_text(paper_id, text)`
  - `LibraryService.get_graph_data` 节点/连线输出新字段
  - 三个 extract 端点在 AI 提取前把正文存库

- [ ] **Step 1: 抽取解析分发（先小重构）**

Create `backend/services/parser_registry.py`：
```python
"""解析服务分发 —— 按存储物理文件选择 PDF / DOCX 解析器"""

import os
from config import PAPER_STORAGE_DIR
from services.pdf_service import PDFService
from services.docx_service import DocxService

pdf_service = PDFService()
docx_service = DocxService()


def get_parser_for_paper(paper_id: str):
    """按物理文件选择解析服务；无文件返回 None"""
    if os.path.exists(os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.pdf")):
        return pdf_service
    if os.path.exists(os.path.join(PAPER_STORAGE_DIR, f"{paper_id}.docx")):
        return docx_service
    return None
```

Modify `backend/routers/knowledge.py`：删除局部 `_get_parser_for_paper`，改为导入并更新 3 处调用点：
```python
from services.parser_registry import get_parser_for_paper
# 原 `parser = _get_parser_for_paper(req.paper_id)` → `parser = get_parser_for_paper(req.paper_id)`
```

- [ ] **Step 2: 写持久化测试（先红）**

Create `backend/tests/test_library_service.py`：
```python
from services.library_service import LibraryService


async def _seed_paper(db, pid="p1", with_text=""):
    if with_text:
        await db.execute(
            "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
            "VALUES (?, 't', 't.pdf', 1, 0, '2026-08-04', 'done', ?)", [pid, with_text])
    else:
        await db.execute(
            "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
            "VALUES (?, 't', 't.pdf', 1, 0, '2026-08-04', 'done')", [pid])
    await db.commit()


async def test_save_concepts_persists_new_fields(db):
    await _seed_paper(db)
    await LibraryService.save_concepts("p1", [{
        "id": "abc", "name": "图谱", "definition": "d", "type": "finding", "page": 2,
        "evidence": "证据", "confidence": 0.6, "confidence_ai": 0.9, "status": "pending",
    }])
    rows = await db.execute_fetchall("SELECT * FROM concepts WHERE slug='abc'")
    assert rows[0]["confidence"] == 0.6
    assert rows[0]["confidence_ai"] == 0.9
    assert rows[0]["evidence"] == "证据"
    assert rows[0]["status"] == "pending"


async def test_save_relations_persists_new_fields(db):
    await _seed_paper(db)
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, created_by, created_at, updated_at) "
        "VALUES ('p1','a','A','', 'finding', 1, 'ai', '2026-08-04', '2026-08-04'), "
        "('p1','b','B','', 'finding', 1, 'ai', '2026-08-04', '2026-08-04')")
    await db.commit()
    await LibraryService.save_relations("p1", [{
        "source": "a", "target": "b", "type": "cites", "evidence": "e",
        "page": 3, "confidence": 0.7, "confidence_ai": 0.8, "status": "pending",
    }])
    rows = await db.execute_fetchall("SELECT * FROM relations")
    assert rows[0]["confidence"] == 0.7
    assert rows[0]["confidence_ai"] == 0.8
    assert rows[0]["page"] == 3


async def test_update_paper_text(db):
    await _seed_paper(db)
    await LibraryService.update_paper_text("p1", "全文内容")
    rows = await db.execute_fetchall("SELECT text FROM papers WHERE id='p1'")
    assert rows[0]["text"] == "全文内容"


async def test_get_graph_data_includes_new_fields(db):
    await _seed_paper(db, with_text="[第1页]\n图谱 图谱 图谱")
    await LibraryService.save_concepts("p1", [{
        "id": "abc", "name": "图谱", "definition": "d", "type": "finding", "page": 1,
        "evidence": "证据", "confidence": 0.6, "confidence_ai": 0.9, "status": "confirmed",
    }])
    data = await LibraryService.get_graph_data("p1")
    node = data["nodes"][0]
    assert node["confidence"] == 0.6
    assert node["confidence_ai"] == 0.9
    assert node["status"] == "confirmed"
    assert node["evidence"] == "证据"
```

- [ ] **Step 3: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_library_service.py -v`
Expected: FAIL — `KeyError: 'confidence'`（save_concepts 未写新列，查询返回 None/缺失）

- [ ] **Step 4: 实现持久化透传**

Modify `backend/services/library_service.py`：

`save_concepts` 改为：
```python
    @staticmethod
    async def save_concepts(paper_id: str, concepts: list[dict]):
        db = await get_db()
        now = datetime.now().isoformat()
        for c in concepts:
            await db.execute(
                "INSERT OR REPLACE INTO concepts "
                "(paper_id, slug, name, definition, type, page, evidence, confidence, confidence_ai, status, created_by, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ai', ?, ?)",
                [paper_id, c["id"], c["name"], c["definition"], c["type"], c["page"],
                 c.get("evidence", ""), c.get("confidence", 0.5), c.get("confidence_ai"),
                 c.get("status", "pending"), now, now]
            )
        await db.commit()
```

`save_relations` 改为：
```python
    @staticmethod
    async def save_relations(paper_id: str, relations: list[dict]):
        db = await get_db()
        now = datetime.now().isoformat()
        for r in relations:
            await db.execute(
                "INSERT INTO relations "
                "(paper_id, source_slug, target_slug, type, evidence, page, confidence, confidence_ai, status, created_by, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ai', ?, ?)",
                [paper_id, r["source"], r["target"], r["type"], r.get("evidence", ""),
                 r.get("page"), r.get("confidence", 0.5), r.get("confidence_ai"),
                 r.get("status", "pending"), now, now]
            )
        await db.commit()
```

新增：
```python
    @staticmethod
    async def update_paper_text(paper_id: str, text: str):
        db = await get_db()
        await db.execute("UPDATE papers SET text = ? WHERE id = ?", [text, paper_id])
        await db.commit()
```

`get_graph_data` 节点 dict 追加：
```python
            "evidence": c.get("evidence", ""),
            "confidence": c.get("confidence", 0.5),
            "confidence_ai": c.get("confidence_ai"),
            "status": c.get("status", "pending"),
```
连线 dict 追加：
```python
            "confidence": r.get("confidence", 0.5),
            "confidence_ai": r.get("confidence_ai"),
            "status": r.get("status", "pending"),
            "page": r.get("page"),
```

- [ ] **Step 5: extract 端点存正文**

Modify `backend/routers/knowledge.py` 三个 extract 端点，在调用 AI 之前存正文：
- `/extract`：解析到 `paper` 后加 `await LibraryService.update_paper_text(req.paper_id, paper["full_text"])`
- `/extract-text`：创建论文后加 `await LibraryService.update_paper_text(paper_id, req.text)`
- `/extract-url`：创建论文后加 `await LibraryService.update_paper_text(paper_id, text)`

- [ ] **Step 6: 跑全部后端测试确认通过**

Run: `cd backend && python -m pytest -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/services/library_service.py backend/services/parser_registry.py backend/routers/knowledge.py backend/tests/test_library_service.py
git commit -m "feat(persist): 新字段持久化透传 + 论文正文入库 + 解析分发抽取"
```

---

### Task 6: 状态更新 + 存量置信度回填

**Files:**
- Modify: `backend/models/schemas.py`
- Modify: `backend/services/confidence_service.py`（追加 `backfill_paper_confidences`）
- Modify: `backend/routers/knowledge.py`
- Create: `backend/scripts/backfill_confidence.py`
- Create: `backend/tests/test_backfill.py`

**Interfaces:**
- Consumes: `confidence_service.text_signal_for_concept/_relation`、`LibraryService`、`parser_registry.get_parser_for_paper`
- Produces:
  - `ConceptUpdate.status` / `RelationUpdate.status` 可选字段；`PUT` 端点接受并写库
  - `confidence_service.backfill_paper_confidences(db, paper_id) -> dict` — 返回 `{concepts, relations}` 处理数；无正文时跳过（返回 0,0）
  - `POST /api/system/backfill-confidence?paper_id=` 端点 — 返回 `{processed, concepts, relations}`
  - `backend/scripts/backfill_confidence.py` CLI

- [ ] **Step 1: 写回填测试（先红）**

Create `backend/tests/test_backfill.py`：
```python
from services.confidence_service import backfill_paper_confidences


async def test_backfill_recomputes_confidence(db):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status, text) "
        "VALUES ('p1','t','t.pdf',1,0,'2026-08-04','done','[第1页]\\n图谱 图谱 图谱')")
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, confidence, confidence_ai, status, created_by, created_at, updated_at) "
        "VALUES ('p1','abc','图谱','d','finding',1,0.9,0.9,'pending','ai','2026-08-04','2026-08-04')")
    await db.commit()

    result = await backfill_paper_confidences(db, "p1")
    assert result["concepts"] == 1
    rows = await db.execute_fetchall("SELECT confidence, confidence_ai FROM concepts WHERE slug='abc'")
    assert rows[0]["confidence_ai"] is None
    assert rows[0]["confidence"] > 0.5  # 纯文本信号重算（正文出现 3 次 → 高信号）


async def test_backfill_skips_without_text(db):
    await db.execute(
        "INSERT INTO papers (id, title, filename, page_count, text_length, upload_time, extract_status) "
        "VALUES ('p1','t','t.pdf',1,0,'2026-08-04','done')")
    await db.execute(
        "INSERT INTO concepts (paper_id, slug, name, definition, type, page, confidence, confidence_ai, status, created_by, created_at, updated_at) "
        "VALUES ('p1','abc','图谱','d','finding',1,0.9,0.9,'pending','ai','2026-08-04','2026-08-04')")
    await db.commit()

    result = await backfill_paper_confidences(db, "p1")
    assert result["concepts"] == 0  # 无正文 → 跳过
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_backfill.py -v`
Expected: FAIL — `ImportError: cannot import name 'backfill_paper_confidences'`

- [ ] **Step 3: 实现回填函数**

Modify `backend/services/confidence_service.py`，追加：
```python
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
```

- [ ] **Step 4: schemas 加 status + 证据请求模型**

Modify `backend/models/schemas.py`：
```python
class ConceptUpdate(BaseModel):
    name: Optional[str] = None
    definition: Optional[str] = None
    type: Optional[str] = None
    page: Optional[int] = None
    status: Optional[str] = None

class RelationUpdate(BaseModel):
    type: Optional[str] = None
    evidence: Optional[str] = None
    status: Optional[str] = None

class EvidenceContextRequest(BaseModel):
    evidence: str
```

- [ ] **Step 5: update 端点接受 status + 回填/证据端点**

Modify `backend/routers/knowledge.py`：
- 顶部导入追加 `from services.confidence_service import backfill_paper_confidences`、`from services.evidence_service import evidence_context_for_paper`、`from models.schemas import EvidenceContextRequest`
- `update_concept` 的可更新字段列表 `["name", "definition", "type", "page"]` 改为 `["name", "definition", "type", "page", "status"]`
- `update_relation` 中 `if req.evidence is not None:` 之后追加：
```python
    if req.status is not None:
        updates.append("status = ?"); params.append(req.status)
```
- 新增端点：
```python
@router.post("/system/backfill-confidence")
async def backfill_confidence(paper_id: str = ""):
    """存量论文置信度回填（纯文本信号）；指定 paper_id 则只处理该篇"""
    from database import get_db
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
        total_c += result["concepts"]; total_r += result["relations"]
        processed += 1
    return R.success(data={"processed": processed, "concepts": total_c, "relations": total_r})


@router.post("/papers/{paper_id}/evidence-context")
async def evidence_context(paper_id: str, req: EvidenceContextRequest):
    """返回证据串在原文中的上下文与页码；无正文/找不到时 found=False"""
    from database import get_db
    db = await get_db()
    return R.success(data=await evidence_context_for_paper(db, paper_id, req.evidence))
```

> 注：端点本身是薄胶水，其核心逻辑 `evidence_context_for_paper` 已在 Task 3 有单元测试，端点由 Task 10 手动验收覆盖，不再重复写 TestClient 测试（避免引入 httpx 依赖）。

- [ ] **Step 6: 写回填 CLI 脚本**

Create `backend/scripts/backfill_confidence.py`：
```python
"""存量论文置信度回填 CLI：python -m scripts.backfill_confidence [paper_id]

不传 paper_id 则处理全部论文。演示前跑一次，让旧论文带上文本信号置信度。
"""
import asyncio
import sys

from database import init_db, get_db, close_db
from services.parser_registry import get_parser_for_paper
from services.confidence_service import backfill_paper_confidences
from services.library_service import LibraryService


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
        total_c += result["concepts"]; total_r += result["relations"]
        print(f"{pid}: {result['concepts']} 概念, {result['relations']} 关系")

    print(f"完成：{len(ids)} 篇，{total_c} 概念，{total_r} 关系")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 7: 跑全部后端测试确认通过**

Run: `cd backend && python -m pytest -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/models/schemas.py backend/services/confidence_service.py backend/routers/knowledge.py backend/scripts/ backend/tests/test_backfill.py
git commit -m "feat(verify): 状态更新 + 存量置信度回填（脚本+端点）"
```

---

### Task 7: 前端 API + 状态工具 + 图谱印章/虚线渲染

**Files:**
- Modify: `frontend/src/api/index.js`
- Create: `frontend/src/utils/confidence.js`
- Create: `frontend/src/utils/__tests__/confidence.test.js`
- Modify: `frontend/src/components/KnowledgeGraph.vue`

**Interfaces:**
- Consumes: 后端节点/连线新字段
- Produces:
  - `evidenceContext(paperId, evidence)` / `backfillConfidence(paperId?)` API
  - `utils/confidence.js`：`LOW_CONFIDENCE_THRESHOLD`、`isLowConfidence(conf)`、`nodeStatusVisual(d)`、`STATUS_LABELS`、`statusLabel(s)`、`confPercent(c)`
  - KnowledgeGraph 节点按状态盖"验"印章 / 虚线描边；连线按状态虚线 + 透明度

- [ ] **Step 1: 写工具函数测试（先红）**

Create `frontend/src/utils/__tests__/confidence.test.js`：
```js
import { describe, it, expect } from 'vitest'
import { isLowConfidence, nodeStatusVisual, statusLabel, confPercent } from '@/utils/confidence'

describe('confidence utils', () => {
  it('isLowConfidence 阈值', () => {
    expect(isLowConfidence(0.5)).toBe(true)
    expect(isLowConfidence(0.6)).toBe(false)
    expect(isLowConfidence(undefined)).toBe(false)
  })

  it('已确认节点盖印章、不虚化', () => {
    const v = nodeStatusVisual({ status: 'confirmed', confidence: 0.5 })
    expect(v.seal).toBe(true)
    expect(v.dashed).toBe(false)
    expect(v.opacity).toBe(1)
  })

  it('未确认低置信 → 虚线 + 明显虚化', () => {
    const v = nodeStatusVisual({ status: 'pending', confidence: 0.4 })
    expect(v.seal).toBe(false)
    expect(v.dashed).toBe(true)
    expect(v.opacity).toBeLessThan(0.7)
  })

  it('未确认高置信 → 虚线但轻度虚化', () => {
    const v = nodeStatusVisual({ status: 'pending', confidence: 0.9 })
    expect(v.dashed).toBe(true)
    expect(v.opacity).toBeGreaterThan(0.7)
  })

  it('状态与置信度文案', () => {
    expect(statusLabel('confirmed')).toBe('已确认')
    expect(statusLabel(undefined)).toBe('待确认')
    expect(confPercent(0.55)).toBe('55%')
    expect(confPercent(undefined)).toBe('—')
  })
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run src/utils/__tests__/confidence.test.js`
Expected: FAIL — `Failed to resolve import "@/utils/confidence"`

- [ ] **Step 3: 实现工具函数**

Create `frontend/src/utils/confidence.js`：
```js
export const LOW_CONFIDENCE_THRESHOLD = 0.6

export function isLowConfidence(conf) {
  return typeof conf === 'number' && conf < LOW_CONFIDENCE_THRESHOLD
}

// 节点/连线的状态视觉：已确认 → 印章 + 实色；未确认 → 虚线（低置信更虚）
export function nodeStatusVisual(d) {
  const confirmed = d?.status === 'confirmed'
  const low = isLowConfidence(d?.confidence)
  return {
    seal: confirmed,
    dashed: !confirmed,
    opacity: confirmed ? 1 : low ? 0.6 : 0.8,
  }
}

export const STATUS_LABELS = { pending: '待确认', confirmed: '已确认', rejected: '已驳回' }

export function statusLabel(s) {
  return STATUS_LABELS[s] || s || '待确认'
}

export function confPercent(c) {
  return typeof c === 'number' ? `${Math.round(c * 100)}%` : '—'
}
```

- [ ] **Step 4: 加 API 封装**

Modify `frontend/src/api/index.js`，在「── 全局探索 ──」之前追加：
```js
// ── 可信抽取 ──
export function evidenceContext(paperId, evidence) {
  return api.post(`/papers/${paperId}/evidence-context`, { evidence })
}
export function backfillConfidence(paperId) {
  return api.post('/system/backfill-confidence', null, { params: paperId ? { paper_id: paperId } : {} })
}
```

- [ ] **Step 5: 图谱状态渲染**

Modify `frontend/src/components/KnowledgeGraph.vue`：
- 顶部导入：`import { nodeStatusVisual } from '@/utils/confidence'`
- 节点主体 circle 追加状态视觉：
```js
  nodeGroups.append('circle')
    .attr('r', 18)
    .attr('fill', '#111827')
    .attr('stroke', d => nodeStroke(d))
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', d => nodeStatusVisual(d).dashed ? '4,3' : null)
    .attr('opacity', d => nodeStatusVisual(d).opacity)
    .attr('style', d => `filter: drop-shadow(0 0 6px ${d.color})`)
```
- 在 text 元素之后追加印章（仅已确认节点）：
```js
  const sealG = nodeGroups.filter(d => nodeStatusVisual(d).seal).append('g')
    .attr('class', 'node-seal')
    .attr('pointer-events', 'none')
  sealG.append('rect')
    .attr('x', -7).attr('y', 20).attr('width', 14).attr('height', 12).attr('rx', 2)
    .attr('fill', 'none').attr('stroke', '#e8453c').attr('stroke-width', 1.2)
  sealG.append('text')
    .attr('x', 0).attr('y', 29.5)
    .attr('text-anchor', 'middle').attr('font-size', 8).attr('font-weight', 700)
    .attr('fill', '#e8453c')
    .text('验')
```
- 边渲染：class 化 + 状态虚化。`linkLines` 的 `join('line')` 后追加：
```js
    .attr('class', d => nodeStatusVisual(d).dashed ? 'link-dashed' : 'link-solid')
    .attr('opacity', d => nodeStatusVisual(d).opacity)
```
- 把末尾 CSS 中 `:deep(g line) { animation: link-flow 4s linear infinite; stroke-dasharray: 6 4; }` 替换为：
```css
:deep(g line.link-dashed) { animation: link-flow 4s linear infinite; stroke-dasharray: 6 4; }
:deep(g line.link-solid) { stroke-dasharray: none; }
```
（`link-flow` keyframes 保持不变；原 `stroke-dasharray` 的 `contradicts` 判断属性因被 CSS 覆盖而不再起作用，可一并移除。）
- 图例补状态说明（spec 要求）：在「概念」行与「关系」行之间插入一行（保证关系行仍是 `:last-child`，其线型样式不回归）：
```html
      <div class="legend-row">
        <span class="legend-label">状态</span>
        <span class="legend-chip"><i class="legend-seal"></i>人工验证</span>
        <span class="legend-chip"><i class="legend-dash"></i>待确认/低置信</span>
      </div>
```
style 追加：
```css
.legend-row .legend-seal { width: 10px; height: 10px; border: 1px solid #e8453c; border-radius: 2px; background: transparent; }
.legend-row .legend-dash { width: 14px; height: 2px; border-top: 2px dashed rgba(255,255,255,0.5); background: transparent; border-radius: 0; }
```

- [ ] **Step 6: 跑前端测试确认通过**

Run: `cd frontend && npx vitest run src/utils/__tests__/confidence.test.js`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/index.js frontend/src/utils/confidence.js frontend/src/utils/__tests__/confidence.test.js frontend/src/components/KnowledgeGraph.vue
git commit -m "feat(graph): 图谱状态渲染——印章/虚线/虚化 + 可信API封装"
```

---

### Task 8: 侧栏状态徽章 + 置信度展示 + 确认/驳回

**Files:**
- Modify: `frontend/src/views/WorkbenchView.vue`
- Modify: `frontend/src/components/ConceptEditor.vue`
- Modify: `frontend/src/components/RelationEditor.vue`
- Create: `frontend/src/components/__tests__/ConceptEditor.test.js`

**Interfaces:**
- Consumes: `utils/confidence.js`（Task 7）、`api.updateConcept/updateRelation`
- Produces: 概念/关系卡片的 状态徽章 + 置信度 + 低置信提示 + 原文片段 + 确认/驳回按钮；Workbench 的 `onConfirmConcept/onRejectConcept/onConfirmRelation/onRejectRelation`

- [ ] **Step 1: 写组件测试（先红）**

Create `frontend/src/components/__tests__/ConceptEditor.test.js`：
```js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConceptEditor from '../ConceptEditor.vue'

const baseConcept = {
  id: 'abc', name: '图谱', definition: '知识结构', type: 'finding', page: 2,
  evidence: '图谱是知识结构', confidence: 0.55, status: 'pending',
}

// stub Element Plus 按钮：attrs（含 data-test）透传到根元素，避免组件未注册告警
const stubs = { 'el-button': { template: '<button><slot /></button>' } }
const opts = { global: { stubs } }

describe('ConceptEditor 只读模式', () => {
  it('显示状态徽章、置信度与低置信提示', () => {
    const wrapper = mount(ConceptEditor, { props: { concept: baseConcept, editing: false }, ...opts })
    expect(wrapper.text()).toContain('待确认')
    expect(wrapper.text()).toContain('55%')
    expect(wrapper.text()).toContain('建议人工确认')
    expect(wrapper.text()).toContain('图谱是知识结构')
  })

  it('点击确认/驳回触发事件', async () => {
    const wrapper = mount(ConceptEditor, { props: { concept: baseConcept, editing: false }, ...opts })
    await wrapper.find('[data-test="confirm"]').trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
    await wrapper.find('[data-test="reject"]').trigger('click')
    expect(wrapper.emitted('reject')).toBeTruthy()
  })

  it('已确认概念显示印章文案、不显示确认按钮', () => {
    const wrapper = mount(ConceptEditor, { props: { concept: { ...baseConcept, status: 'confirmed' }, editing: false }, ...opts })
    expect(wrapper.text()).toContain('已确认')
    expect(wrapper.find('[data-test="confirm"]').exists()).toBe(false)
  })
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run src/components/__tests__/ConceptEditor.test.js`
Expected: FAIL（组件无 status/confirm 相关渲染）

- [ ] **Step 3: 升级 ConceptEditor**

Modify `frontend/src/components/ConceptEditor.vue`：
- script 导入：`import { isLowConfidence, statusLabel, confPercent } from '@/utils/confidence'`
- 只读模板（`v-if="!editing && concept"` 块内）改为：
```html
      <h3 class="ce-name">{{ concept.name }}</h3>
      <div class="ce-status-row">
        <span class="ce-status-badge" :class="concept.status">{{ statusLabel(concept.status) }}</span>
        <span class="ce-conf">置信度 {{ confPercent(concept.confidence) }}</span>
      </div>
      <p v-if="isLowConfidence(concept.confidence)" class="ce-lowhint">低置信，建议人工确认</p>
      <p class="ce-def">{{ concept.definition }}</p>
      <div class="ce-meta">
        <span>原文页码：第 {{ concept.page }} 页</span>
      </div>
      <div v-if="concept.evidence" class="ce-evidence">
        <span class="ce-evidence-label">原文片段</span>
        <p class="ce-evidence-text">{{ concept.evidence }}</p>
      </div>
      <div v-if="concept.status !== 'confirmed'" class="ce-confirm-actions">
        <el-button size="small" type="primary" data-test="confirm" @click="$emit('confirm')">确认</el-button>
        <el-button size="small" data-test="reject" @click="$emit('reject')">驳回</el-button>
      </div>
```
- `defineEmits` 加 `'confirm', 'reject'`。
- style 追加：
```css
.ce-status-row { display: flex; align-items: center; gap: var(--space-sm); margin-bottom: var(--space-sm); }
.ce-status-badge { padding: 2px 8px; border-radius: 12px; font-size: var(--text-xs); font-weight: 600; }
.ce-status-badge.pending { color: #f59e0b; border: 1px solid #f59e0b; }
.ce-status-badge.confirmed { color: #10b981; border: 1px solid #10b981; }
.ce-status-badge.rejected { color: var(--text-muted); border: 1px solid var(--border-strong); }
.ce-conf { font-size: var(--text-xs); color: var(--text-muted); }
.ce-lowhint { font-size: var(--text-xs); color: #f59e0b; margin-bottom: var(--space-sm); }
.ce-evidence { margin-bottom: var(--space-lg); }
.ce-evidence-label { font-size: var(--text-xs); color: var(--text-muted); }
.ce-evidence-text { font-size: var(--text-sm); color: var(--text-secondary); font-style: italic; border-left: 2px solid var(--vermilion); padding-left: var(--space-sm); margin-top: 4px; line-height: 1.6; }
.ce-confirm-actions { display: flex; gap: var(--space-sm); margin-top: var(--space-sm); }
```

- [ ] **Step 4: 升级 RelationEditor**

Modify `frontend/src/components/RelationEditor.vue`：
- script 导入：`import { isLowConfidence, statusLabel, confPercent } from '@/utils/confidence'`
- 在证据段落（`<p class="re-evidence" ...>`）之后追加：
```html
    <div class="re-status-row">
      <span class="re-status-badge" :class="link.status">{{ statusLabel(link.status) }}</span>
      <span class="re-conf">置信度 {{ confPercent(link.confidence) }}</span>
    </div>
    <p v-if="isLowConfidence(link.confidence)" class="re-lowhint">低置信，建议人工确认</p>
    <div v-if="link.status !== 'confirmed'" class="re-confirm-actions">
      <el-button size="small" type="primary" data-test="confirm" @click="$emit('confirm')">确认</el-button>
      <el-button size="small" data-test="reject" @click="$emit('reject')">驳回</el-button>
    </div>
```
- `defineEmits` 加 `'confirm', 'reject'`。
- style 追加：
```css
.re-status-row { display: flex; align-items: center; gap: var(--space-sm); margin-bottom: var(--space-sm); }
.re-status-badge { padding: 2px 8px; border-radius: 12px; font-size: var(--text-xs); font-weight: 600; }
.re-status-badge.pending { color: #f59e0b; border: 1px solid #f59e0b; }
.re-status-badge.confirmed { color: #10b981; border: 1px solid #10b981; }
.re-status-badge.rejected { color: var(--text-muted); border: 1px solid var(--border-strong); }
.re-conf { font-size: var(--text-xs); color: var(--text-muted); }
.re-lowhint { font-size: var(--text-xs); color: #f59e0b; margin-bottom: var(--space-sm); }
.re-confirm-actions { display: flex; gap: var(--space-sm); margin-top: var(--space-sm); }
```

- [ ] **Step 5: Workbench 接线确认/驳回**

Modify `frontend/src/views/WorkbenchView.vue`：
- 导入：`import { updateConcept, updateRelation } from '@/api'`
- ConceptEditor 用法追加事件：
```html
          @confirm="onConfirmConcept(store.selectedNode.id)"
          @reject="onRejectConcept(store.selectedNode.id)"
```
- RelationEditor 用法追加事件：
```html
          @confirm="onConfirmRelation(store.selectedLink.relId)"
          @reject="onRejectRelation(store.selectedLink.relId)"
```
- script 追加处理器：
```js
async function onConfirmConcept(slug) {
  try {
    await updateConcept(paperId, slug, { status: 'confirmed' })
    ElMessage.success('已确认该概念')
    await reload()
  } catch (e) { ElMessage.error(e.message || '确认失败') }
}
async function onRejectConcept(slug) {
  try {
    await updateConcept(paperId, slug, { status: 'rejected' })
    ElMessage.success('已驳回')
    await reload()
  } catch (e) { ElMessage.error(e.message || '操作失败') }
}
async function onConfirmRelation(relId) {
  try {
    await updateRelation(paperId, relId, { status: 'confirmed' })
    ElMessage.success('已确认该关系')
    await reload()
  } catch (e) { ElMessage.error(e.message || '确认失败') }
}
async function onRejectRelation(relId) {
  try {
    await updateRelation(paperId, relId, { status: 'rejected' })
    ElMessage.success('已驳回')
    await reload()
  } catch (e) { ElMessage.error(e.message || '操作失败') }
}
```

- [ ] **Step 6: 跑前端测试确认通过**

Run: `cd frontend && npx vitest run`
Expected: PASS（含新 ConceptEditor 测试与既有测试）

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/WorkbenchView.vue frontend/src/components/ConceptEditor.vue frontend/src/components/RelationEditor.vue frontend/src/components/__tests__/ConceptEditor.test.js
git commit -m "feat(verify): 侧栏状态徽章/置信度/确认驳回交互"
```

---

### Task 9: 证据弹窗 + 低置信聚合提醒（含"只看待确认"过滤）

**Files:**
- Create: `frontend/src/components/EvidenceDialog.vue`
- Create: `frontend/src/components/__tests__/EvidenceDialog.test.js`
- Modify: `frontend/src/views/WorkbenchView.vue`
- Modify: `frontend/src/stores/graph.js`
- Modify: `frontend/src/stores/__tests__/graph.test.js`
- Modify: `frontend/src/components/KnowledgeGraph.vue`

**Interfaces:**
- Consumes: `api.evidenceContext`（Task 7）、`utils/confidence.js`（Task 7）
- Produces: `EvidenceDialog` 组件（`open(text)` 暴露方法）；Workbench 的 `evidenceDialogRef` + `openEvidence(text)`；低置信聚合统计条；graph store 新增 `filterPending` 状态 + `togglePendingFilter()`，"只看待确认" 过滤

- [ ] **Step 1: 写组件测试（先红）**

Create `frontend/src/components/__tests__/EvidenceDialog.test.js`：
```js
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import EvidenceDialog from '../EvidenceDialog.vue'
import * as api from '@/api'

vi.mock('@/api', () => ({ evidenceContext: vi.fn() }))

// el-dialog 默认 teleport 到 body，wrapper.find 找不到内容 → 用 stub 内联渲染 slot
const stubs = { 'el-dialog': { template: '<div class="ev-dialog-stub"><slot /></div>' } }
const opts = { global: { stubs } }

describe('EvidenceDialog', () => {
  beforeEach(() => { api.evidenceContext.mockReset() })

  it('打开后展示上下文与页码，证据串高亮', async () => {
    // context = "前文 图谱是知识结构 后文"，start=3/end=10 → 高亮"图谱是知识结构"
    api.evidenceContext.mockResolvedValue({
      found: true, context: '前文 图谱是知识结构 后文', start: 3, end: 10, page: 2,
    })
    const wrapper = mount(EvidenceDialog, { props: { paperId: 'p1' }, ...opts })
    wrapper.vm.open('图谱是知识结构')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('第 2 页')
    expect(wrapper.find('.ev-hit').text()).toBe('图谱是知识结构')
  })

  it('找不到证据时显示原因', async () => {
    api.evidenceContext.mockResolvedValue({ found: false, reason: '未找到证据串' })
    const wrapper = mount(EvidenceDialog, { props: { paperId: 'p1' }, ...opts })
    wrapper.vm.open('不存在')
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('未找到证据串')
  })
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd frontend && npx vitest run src/components/__tests__/EvidenceDialog.test.js`
Expected: FAIL — `Failed to resolve import "../EvidenceDialog.vue"`

- [ ] **Step 3: 实现 EvidenceDialog**

Create `frontend/src/components/EvidenceDialog.vue`：
```vue
<template>
  <el-dialog title="原文证据" v-model="visible" width="560px" append-to-body>
    <div v-if="loading" class="ev-loading">定位中…</div>
    <div v-else-if="!data?.found" class="ev-empty">{{ data?.reason || '原文不可用' }}</div>
    <template v-else>
      <div class="ev-meta">页码：第 {{ data.page }} 页</div>
      <p class="ev-context" v-html="highlighted"></p>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { evidenceContext } from '@/api'

const props = defineProps({ paperId: { type: String, required: true } })

const visible = ref(false)
const loading = ref(false)
const data = ref(null)

function open(text) {
  data.value = null
  visible.value = true
  loading.value = true
  evidenceContext(props.paperId, text || '')
    .then(res => { data.value = res })
    .catch(() => { data.value = { found: false, reason: '查询失败' } })
    .finally(() => { loading.value = false })
}

const highlighted = computed(() => {
  if (!data.value?.context) return ''
  const { context, start, end } = data.value
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return `${esc(context.slice(0, start))}<mark class="ev-hit">${esc(context.slice(start, end))}</mark>${esc(context.slice(end))}`
})

defineExpose({ open })
</script>

<style scoped>
.ev-loading, .ev-empty { color: var(--text-muted); font-size: var(--text-sm); text-align: center; padding: var(--space-lg) 0; }
.ev-meta { font-size: var(--text-xs); color: var(--text-muted); margin-bottom: var(--space-sm); }
.ev-context { font-size: var(--text-sm); color: var(--text-secondary); line-height: 1.8; white-space: pre-wrap; }
.ev-hit { background: rgba(232, 69, 60, 0.18); color: #fff; padding: 0 2px; border-radius: 2px; }
</style>
```

- [ ] **Step 4: Workbench 接证据弹窗 + 聚合提醒**

Modify `frontend/src/views/WorkbenchView.vue`：
- 导入：`import EvidenceDialog from '@/components/EvidenceDialog.vue'`、`import { isLowConfidence } from '@/utils/confidence'`
- 模板：在 `</aside>` 之后、`<Transition name="weave-fade">` 之前追加：
```html
      <EvidenceDialog ref="evidenceDialogRef" :paper-id="paperId" />
```
- script 追加：
```js
const evidenceDialogRef = ref(null)
function openEvidence(text) { evidenceDialogRef.value?.open(text) }

// 低置信聚合：待确认数 + 低置信数（供评审演示）
const pendingCount = computed(() =>
  store.graphData?.nodes?.filter(n => n.status !== 'confirmed').length ?? 0)
const lowConfCount = computed(() =>
  store.graphData?.nodes?.filter(n => isLowConfidence(n.confidence)).length ?? 0)
```
- 概念编辑器事件追加：
```html
          @evidence="openEvidence(store.selectedNode.evidence)"
```
- 关系编辑器事件追加：
```html
          @evidence="openEvidence(store.selectedLink.evidence)"
```
- ConceptEditor / RelationEditor 的 `defineEmits` 分别追加 `'evidence'`，并给"原文片段" / 证据段落加点击事件：
  - ConceptEditor：`<p class="ce-evidence-text" @click="$emit('evidence')">` + 样式 `cursor: pointer;`
  - RelationEditor：`<p class="re-evidence" @click="$emit('evidence')">` + `cursor: pointer;`
- 工作台图谱区域上方（`graph-search` 同级）加聚合条：
```html
        <div class="verify-strip" v-if="store.graphData?.nodes?.length">
          <span>{{ store.graphData.nodes.length }} 个概念</span>
          <span class="vs-item" :class="{ warn: pendingCount > 0, active: store.filterPending }" @click="store.togglePendingFilter()">{{ pendingCount }} 待确认</span>
          <span class="vs-item" :class="{ warn: lowConfCount > 0 }">{{ lowConfCount }} 低置信</span>
        </div>
```
- style 追加：
```css
.verify-strip { position: absolute; top: var(--space-md); left: var(--space-md); z-index: 5; display: flex; gap: var(--space-sm); align-items: center; font-size: var(--text-xs); color: var(--text-muted); padding: 6px 12px; border-radius: var(--radius-md); background: var(--space-elevated); border: 1px solid var(--border-subtle); }
.verify-strip .vs-item.warn { color: #f59e0b; }
.verify-strip .vs-item.active { color: #fff; background: rgba(255,255,255,0.1); cursor: pointer; }
```

- [ ] **Step 5: graph store 加"只看待确认"过滤**

Modify `frontend/src/stores/graph.js`：在 `clearMultiSelect` 之后追加：
```js
  const filterPending = ref(false)
  function togglePendingFilter() { filterPending.value = !filterPending.value }
```
并在 return 中追加 `filterPending, togglePendingFilter`。

Modify `frontend/src/stores/__tests__/graph.test.js`，追加用例：
```js
  it('togglePendingFilter 切换', () => {
    const s = useGraphStore()
    expect(s.filterPending).toBe(false)
    s.togglePendingFilter()
    expect(s.filterPending).toBe(true)
  })
```

Modify `frontend/src/components/KnowledgeGraph.vue`：
- 在 `watch(() => graphStore.filterType, () => applyFilter())` 后追加 `watch(() => graphStore.filterPending, () => applyFilter())`
- `applyFilter()` 末尾追加（在类型过滤之后）：
```js
  const pf = graphStore.filterPending
  if (pf) {
    svg.selectAll('g g[data-role=node]').attr('opacity', function () {
      const d = d3.select(this).datum()
      return d.status === 'pending' ? 1 : 0.12
    })
    svg.selectAll('line[data-role=link]').attr('opacity', 0.05)
  }
```

- [ ] **Step 6: 跑前端全部测试确认通过**

Run: `cd frontend && npx vitest run`
Expected: PASS（含 EvidenceDialog、graph store 新用例与既有全部测试）

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/EvidenceDialog.vue frontend/src/components/__tests__/EvidenceDialog.test.js frontend/src/views/WorkbenchView.vue frontend/src/stores/graph.js frontend/src/stores/__tests__/graph.test.js frontend/src/components/KnowledgeGraph.vue frontend/src/components/ConceptEditor.vue frontend/src/components/RelationEditor.vue
git commit -m "feat(evidence): 原文证据弹窗 + 低置信聚合提醒 + 只看待确认过滤"
```

---

### Task 10: 端到端手工验收 + 回填脚本验证

**Files:** 无（纯验证）

**Interfaces:**
- Consumes: 全部已完成任务

- [ ] **Step 1: 安装依赖并启动后端**

Run: `cd backend && pip install -r requirements.txt && python -m uvicorn main:app --port 8000`
Expected: 启动无报错（迁移自动执行）

- [ ] **Step 2: 运行回填脚本**

Run: `cd backend && python -m scripts.backfill_confidence`
Expected: 输出每篇论文的概念/关系数，无异常

- [ ] **Step 3: 启动前端并走一遍验收路径**

Run: `cd frontend && npm run dev`
验收路径（手动）：
1. 打开已有论文 → 图谱节点应显示虚线描边 + 部分虚化
2. 点"原文片段" → 证据弹窗显示上下文 + 页码，证据串高亮
3. 侧栏概念 → 显示"待确认"徽章 + 置信度；低置信有提示
4. 点"确认" → 徽章变"已确认"，图谱节点盖上"验"印章、恢复实线
5. 顶部聚合条显示"待确认 / 低置信"计数
6. 上传一篇新 PDF → AI 提取后概念带 evidence/confidence，与上述一致

- [ ] **Step 4: 记录验收结果**

在 commit message 或本文件末尾记录：哪几篇论文回填成功、新提取是否带置信度、确认/印章/证据弹窗是否如预期。

- [ ] **Step 5: Commit（若有收尾修复）**

```bash
git add -A
git commit -m "fix(verify): 端到端验收收尾修复"
```
（若验收中发现 bug，先修再提交；无则跳过。）
