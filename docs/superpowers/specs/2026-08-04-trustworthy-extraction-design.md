# 可信抽取：证据、置信度与人工确认

日期：2026-08-04
状态：已通过头脑风暴评审

## 背景与目标

「织识」从"AI 论文图谱工具"升级为"可证明可信、可交互探索、可讲故事的学术知识重构引擎"。本子项目是赛事级升级方案的第一步——**可信抽取**，为后续评测体系、融合算法、研究闭环打地基。

**目标**：给概念和关系增加证据页码、原文片段、置信度、人工确认状态，避免只展示 AI JSON。让评审看到一条"AI 提取 → 置信度交叉验证 → 人工确认"的可信链路。

## 现状差距

- 数据模型已有：`concepts(page)`、`relations(evidence)`、`concept_merges`、跨论文融合/合并建议
- AI 抽取已出 JSON，分片合并、容错解析成熟
- **缺口**：置信度、人工确认状态、概念级原文证据不存在；`papers` 表未存正文，证据检索与置信度回填缺原材料；前端无原文证据展示

## 数据模型与迁移

### 新增列

| 表 | 新增列 | 说明 |
|---|---|---|
| `papers` | `text` TEXT DEFAULT '' | 正文缓存（证据检索 + 置信度回填原材料） |
| `concepts` | `evidence` TEXT DEFAULT '' | 该概念在原文的核心论述片段（直接引用） |
| `concepts` | `confidence` REAL DEFAULT 0.5 | 最终置信度（AI×文本信号交叉） |
| `concepts` | `confidence_ai` REAL | AI 自评分（保留原始值，展示交叉过程；存量回填为 NULL） |
| `concepts` | `status` TEXT DEFAULT 'pending' | `pending` / `confirmed` / `rejected`（rejected 仅标记，保留在图上，可由过滤隐藏） |
| `relations` | `confidence` / `confidence_ai` / `status` | 同上 |
| `relations` | `page` INTEGER | 证据页码（AI 报告，缺失则 NULL，不阻塞） |

### 迁移机制

`database.py` 新增幂等 `migrate_schema()`：`PRAGMA table_info(<table>)` 查现有列 → 缺失列才 `ALTER TABLE ADD COLUMN`。在 `init_db()` 中紧随建表调用，确保已存在数据库升级安全。存量数据不动，由回填脚本补置信度。

## AI 抽取升级

`KNOWLEDGE_EXTRACTION_PROMPT` 升级：

- **概念**新增 `evidence`（原文中最能定义该概念的一句话，直接引用）、`confidence`（0-1，对"该概念真实存在于论文"的判断把握）
- **关系**新增 `confidence`（0-1）、`page`（证据所在页码，缺失容忍）

### 容错解析（风险核心）

- `confidence` 缺失 → 默认 0.5（会被文本信号交叉修正）；越界 → clamp 到 [0,1]
- 概念 `evidence` 缺失 → 默认空串，侧栏显示"无原文片段"
- `GraphService.build_graph` 与 `LibraryService.save_concepts/save_relations` 同步透传新字段

## 置信度算法

新文件 `backend/services/confidence_service.py`：

```
概念文本信号 = min(1.0, 出现次数/3) × (0.7 + 0.3 × 是否出现在摘要/引言开头10%或结论结尾15%)

关系文本信号 = 0.5 × (证据串能否在全文定位) + 0.5 × (两端概念文本信号均值)

最终置信度 = sqrt(ai自评 × 文本信号)   # 几何平均，偏严格——两者都高才算高
```

几何平均是"可证明可信"叙事的关键：**AI 说 0.9 但论文里只出现 2 次、不在摘要里 → 文本信号 0.4 → 最终 0.55 → 系统自动标记"建议人工确认"**。

### 存量回填

老论文没有 AI 自评分 → 最终置信度 = 纯文本信号，`confidence_ai` 置 NULL。做成独立脚本 `backend/scripts/backfill_confidence.py`（重新解析物理文件 → 补 `papers.text` → 算文本信号）。演示前跑一次。文本/URL 旧论文无物理文件可解析，标"原文不可用"。

## 后端接口

1. `POST /api/papers/{paper_id}/evidence-context`
   - 请求体 `{evidence: string}`
   - 在 `papers.text` 中定位证据串，返回 `{context, start, end, page}`（上下文为证据句前后各 150 字符，`start/end` 供前端高亮）
   - 找不到时简单模糊匹配（跳过标点/空白），仍无果返回 `{found: false}`，前端显示"原文不可用"
   - 页码取自该概念/关系已存的 `page`（前端传入）

2. **状态更新并入现有 update 模型**：`ConceptUpdate` / `RelationUpdate` 加 `status` 字段 → 复用 `PUT /graph/{paper_id}/concepts/{slug}` 与 `PUT /graph/{paper_id}/relations/{rel_id}`。避免接口面膨胀。

3. `POST /api/system/backfill-confidence`：脚本的 HTTP 版，返回 `{processed, updated}`，方便演示时点一下触发。

### 响应改造

`get_graph_data` 与提取返回的 d3 数据：节点加 `confidence / confidence_ai / status / evidence`；连线加 `confidence / confidence_ai / status / page`。

## 前端交互

**图谱渲染**（`KnowledgeGraph.vue`）：
- 已确认节点/边：盖朱砂色印章（复用 `motion/SealBadge.vue` 或 SVG 小印章）
- 未确认 / 低置信（< 0.6）：节点虚线描边 + 降低不透明度；边同理
- 节点选中时，侧栏展示 `confidence_ai` 与最终 `confidence` 对比

**侧栏徽章 + 确认**（`WorkbenchView.vue` 侧栏）：
- 卡片显示状态徽章（待确认/已确认/已驳回）+ 置信度百分比
- 低置信项显示"建议人工确认"提示条 + 确认 / 驳回按钮（触发一次 PUT status）
- 概念新增"原文片段"展示区

**证据弹窗**：
- 点击卡片上的证据文字 → 调 `evidence-context` → 显示原文上下文，证据串高亮 + 页码；`found: false` 显示"原文不可用"

**低置信聚合提醒**：
- 工作台顶部轻量统计条（如"12 个概念 · 3 待确认 · 2 低置信"），点击筛选图谱只显示待确认项（复用 graph store 过滤）

**图例更新**：补充状态说明（印章=人工已确认、虚线=待确认/低置信）

## 测试计划

**后端 pytest**（`backend/tests/`，新增）：
- `test_schema_migration.py`：迁移幂等（跑两次不报错）、新列正确添加、存量行保留
- `test_confidence_service.py`：文本信号数学（出现次数、位置加权）、几何平均交叉、边界（概念名不在文中、空文本、0/1 极值）
- `test_evidence_context.py`：证据串定位、上下文边界、模糊匹配、找不到返回 `found:false`
- `test_parse_robustness.py`：AI 输出缺 `confidence/evidence` → 默认值兜底、越界 clamp

**前端 vitest**（补现有）：
- graph store：节点/连线新字段的过滤与渲染数据
- 组件：印章/虚线渲染条件、状态徽章切换、证据弹窗请求与 `found:false` 分支

**手动验收路径**：上传论文 → AI 提取带置信度/证据 → 图谱显示印章与虚线 → 点证据出弹窗高亮 → 确认/驳回 → 旧论文跑回填脚本后置信度更新。

## 范围边界（明确不做）

- 完整原文阅读器 / 页码锚点跳转（后续子项目）
- 评测体系（标准样本、准确率/召回率报告）——独立子项目
- 融合算法升级（语义相似度、别名归一、冲突识别、主题聚类）——独立子项目
- 研究工作流闭环（研究问题视角）——独立子项目
- 赛事演示模式——独立子项目
- 删除论文不删物理文件、导出 PNG no-op 等遗留小问题——另行处理
