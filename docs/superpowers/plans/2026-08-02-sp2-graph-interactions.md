# SP2 图谱交互增强 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让图谱"好用"——类型过滤+图例交互、图谱内搜索定位、编辑模式多选/框选。

**Architecture:** 纯前端，改动集中在 `KnowledgeGraph.vue`（D3 交互）+ `WorkbenchView.vue`（UI）+ `stores/graph.js`（状态）。F1 过滤只改 opacity 不重排布局；F3 框选在编辑模式覆盖背景拖拽。

**Tech Stack:** Vue 3 (script setup), D3 v7, Pinia, Element Plus, Vitest.

## Global Constraints
- 改动只允许在 `frontend/src/` 内；后端不动
- 动效只用 `transform`/`opacity`（GPU）
- **不破坏**：单节点拖拽建关系、节点/连线点击选中、编辑模式、撤销/重做、导出 PNG/JSON/MD、ViewSwitcher 切换
- 每任务末尾 `git commit`，在分支 `feature/sp2-graph-interactions`
- 组件接口沿用：`KnowledgeGraph` 现有 props（data/selectedId/editing）+ emits（select-node/select-link/add-relation/edit-node），新增 expose `zoomToNode(id)`
- 设计规格：`docs/superpowers/specs/2026-08-02-sp2-graph-interactions-design.md`

---

### Task 1: graph store 扩展（filterType + 多选状态）

**Files:**
- Modify: `frontend/src/stores/graph.js`
- Test: `frontend/src/stores/__tests__/graph.test.js`

**Interfaces:**
- Produces: `filterType`（String|null）、`selectedNodeIds`（Array）、actions：`toggleFilter(type)`、`setFilter(type)`、`toggleMultiSelect(id)`、`clearMultiSelect()`、`setSelectedNodes(ids)`

- [ ] **Step 1: 写 store 测试**

`src/stores/__tests__/graph.test.js`：
```js
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGraphStore } from '../graph'

describe('graph store 交互状态', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('toggleFilter 切换与取消', () => {
    const s = useGraphStore()
    expect(s.filterType).toBe(null)
    s.toggleFilter('method')
    expect(s.filterType).toBe('method')
    s.toggleFilter('method')
    expect(s.filterType).toBe(null)
  })

  it('多选添加/清空', () => {
    const s = useGraphStore()
    s.toggleMultiSelect('a'); s.toggleMultiSelect('b')
    expect(s.selectedNodeIds).toEqual(['a', 'b'])
    s.toggleMultiSelect('a')
    expect(s.selectedNodeIds).toEqual(['b'])
    s.clearMultiSelect()
    expect(s.selectedNodeIds).toEqual([])
  })

  it('setSelectedNodes 覆盖', () => {
    const s = useGraphStore()
    s.setSelectedNodes(['x', 'y'])
    expect(s.selectedNodeIds).toEqual(['x', 'y'])
  })
})
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/stores/__tests__/graph.test.js`
Expected: FAIL

- [ ] **Step 3: 实现 store 扩展**

`stores/graph.js` 的 setup 内加：
```js
const filterType = ref(null)
const selectedNodeIds = ref([])

function toggleFilter(type) {
  filterType.value = filterType.value === type ? null : type
}
function setFilter(type) {
  filterType.value = type
}
function toggleMultiSelect(id) {
  const i = selectedNodeIds.value.indexOf(id)
  if (i >= 0) selectedNodeIds.value.splice(i, 1)
  else selectedNodeIds.value.push(id)
}
function clearMultiSelect() {
  selectedNodeIds.value = []
}
function setSelectedNodes(ids) {
  selectedNodeIds.value = ids
}
```
（在 return 中导出这些与现有状态/actions 并列；不改动现有 loadGraph/runExtraction/selectNode 等）

- [ ] **Step 4: 运行确认通过**

Run: `npx vitest run src/stores/__tests__/graph.test.js`
Expected: PASS（3 用例）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/stores/graph.js frontend/src/stores/__tests__/graph.test.js
git commit -m "feat(store): graph store 增加类型过滤与多选状态"
```

---

### Task 2: F1 类型过滤 + 图例交互

**Files:**
- Modify: `frontend/src/components/KnowledgeGraph.vue`
- Modify: `frontend/src/views/WorkbenchView.vue`

**Interfaces:**
- Consumes: store `filterType`/`toggleFilter`（Task 1）
- Produces: 图例概念类型项可点击过滤；过滤仅改 opacity 不重排布局

- [ ] **Step 1: 图例概念项可点击**

`KnowledgeGraph.vue` 模板 `.legend-row`（概念区）的类型项加 `:class="{ active: filterType === t.key }"` 与 `@click="toggleFilter(t.key)"`，关系区类型项不加（只概念过滤）。样式：`.legend-chip.active { color: #fff; }` + `.legend-chip` 加 `cursor: pointer`。

- [ ] **Step 2: filterType 状态**

`KnowledgeGraph` 内本地 ref：`const filterType = ref(null)`，`function toggleFilter(k) { filterType.value = filterType.value === k ? null : k; applyFilter() }`。为保持自包含，用组件内状态而非 store（图例就在图组件内）。`watch(() => props.data, () => { render(); applyFilter() })`。

- [ ] **Step 3: applyFilter 只改 opacity**

不重跑 `render()`（避免重排），单独函数：
```js
function applyFilter() {
  const svg = d3.select(svgEl.value)
  const f = filterType.value
  svg.selectAll('g g[data-role=node]').attr('opacity', function () {
    const d = d3.select(this).datum()
    return f && d.type !== f ? 0.12 : 1
  })
  svg.selectAll('g[data-role=link]').attr('opacity', function () {
    const d = d3.select(this).datum()
    if (!f) return 1
    const src = typeof d.source === 'object' ? d.source : null
    const tgt = typeof d.target === 'object' ? d.target : null
    const srcOk = src && src.type === f
    const tgtOk = tgt && tgt.type === f
    return srcOk || tgtOk ? 1 : 0.05
  })
}
```
在 `render()` 里给节点组加 `attr('data-role', 'node')`、给 line 容器加 `attr('data-role', 'link')`（或直接 selection 分组）。`render()` 末尾调用 `applyFilter()`。

> 关键：过滤不重建 DOM、不重跑 `d3.forceSimulation`——只设 opacity 属性。

- [ ] **Step 4: 验证 + 提交**

`cd frontend && npm run build` 通过；`npm test` 通过。
```bash
git add frontend/src/components/KnowledgeGraph.vue
git commit -m "feat(graph): 图例类型点击过滤——淡出非匹配节点/连线"
```

---

### Task 3: F2 图谱内搜索定位

**Files:**
- Modify: `frontend/src/components/KnowledgeGraph.vue`
- Modify: `frontend/src/views/WorkbenchView.vue`

**Interfaces:**
- Produces: `KnowledgeGraph` expose `zoomToNode(id)`；Workbench 顶部搜索框 → 聚焦节点

- [ ] **Step 1: KnowledgeGraph expose zoomToNode(id)**

在 setup 末尾：
```js
function zoomToNode(id) {
  if (!props.data) return
  const node = props.data.nodes.find(n => n.id === id)
  if (!node || !zoomBehavior || !container.value) return
  const W = container.value.clientWidth
  const H = container.value.clientHeight
  const target = { x: node.x ?? 0, y: node.y ?? 0 }
  const k = currentTransform?.k ?? 1
  const k2 = Math.max(k, 1.6)
  const t = d3.zoomIdentity.translate(W / 2 - target.x * k2, H / 2 - target.y * k2).scale(k2)
  d3.select(svgEl.value).transition().duration(500)
    .call(zoomBehavior.transform, t)
  emit('select-node', id)  // 让侧栏显示详情
}
defineExpose({ zoomBy, resetZoom, zoomToNode })
```

- [ ] **Step 2: Workbench 搜索框 + 下拉**

`WorkbenchView.vue`：`activeView === 'graph'` 时在 `.wb-main` 顶部加搜索框（`el-input` + `el-autocomplete` 或自绘下拉）：
- `searchQuery` ref；`searchResults` computed = `store.graphData.nodes.filter(n => n.name.includes(searchQuery)).slice(0, 8)`
- 选中候选 → `graphRef.value.zoomToNode(id)` + `store.selectNode(id)`；清空搜索框
- 样式：搜索框绝对定位在 `.wb-main` 顶部中央，z-index 高于图谱低于工具栏

- [ ] **Step 3: 验证 + 提交**

`npm run build` + `npm test` 通过。
```bash
git add frontend/src/components/KnowledgeGraph.vue frontend/src/views/WorkbenchView.vue
git commit -m "feat(workbench): 图谱内搜索定位——输入匹配概念名并聚焦节点"
```

---

### Task 4: F3 多选 / 框选（编辑模式）

**Files:**
- Modify: `frontend/src/components/KnowledgeGraph.vue`
- Modify: `frontend/src/views/WorkbenchView.vue`

**Interfaces:**
- Consumes: store `selectedNodeIds`/`toggleMultiSelect`/`clearMultiSelect`/`setSelectedNodes`（Task 1）
- Produces: 编辑模式框选、批量移动、批量删除 UI

- [ ] **Step 1: 框选（编辑模式下背景拖拽）**

`KnowledgeGraph`：
- zoom 的 `.filter()` 改为：编辑模式下排除 mousedown（避免背景拖拽触发平移）：`.filter(event => !props.editing || event.type !== 'mousedown')`
- svg 上加 `mousedown`（编辑模式）→ 记录起点，`mousemove` 画 `.box-select` 矩形（`<rect>`，stroke 朱砂虚线、fill 半透明），`mouseup` → 收集矩形内节点（`node.x/node.y` 在投影内，用 `d3.forceSimulation` 的屏幕坐标：`g` 有 `currentTransform`，需把节点坐标乘以 transform 求屏幕位置），`emit('box-select', ids)`，删除矩形
- 只响应背景 mousedown（节点自身的 drag 会 stopPropagation 不触发 svg mousedown）
- 拖拽开始时若有 `selectedNodeIds` 且被拖节点在多选内 → 记录所有选中节点的初始位置；drag 中把位移 delta 应用到所有选中节点；drag 结束恢复正常。单节点（非多选）保持原行为（拖拽建关系需编辑模式下仍工作——注意：当前编辑模式拖节点=建关系。框选拖拽与建关系在编辑模式冲突？）

> **交互裁决（重要）**：当前编辑模式拖节点 = 拖拽建关系（拖源节点到目标节点）。框选是在**空白处**拖。两者不冲突：节点上拖→建关系；空白处拖→框选。批量移动用**非编辑模式**（普通模式下拖节点=移动），多选后普通模式拖任一选中节点→整组移动。因此：
> - 编辑模式：节点拖=建关系（保留），空白拖=框选
> - 普通模式：多选状态下节点拖=整组移动，否则单节点移动

- [ ] **Step 2: 批量移动（普通模式多选时）**

节点 drag handler：`on start` 判断该节点是否在 `selectedNodeIds` 内且在多选集合 → 记录 `dragStartPositions = selected.map(n => ({ id: n.id, x: n.x, y: n.y }))`；`on drag` 计算 `dx = e.x - d.x`（或相对起始），对每个选中节点 `n.fx = dragStartPositions[i].x + dx; n.fy = ...`；`on end` 清空 fx/fy。单节点不在多选时走原逻辑。

- [ ] **Step 3: Workbench 多选面板 + 批量删除**

- 监听 `box-select` 事件 → `store.setSelectedNodes(ids)` + 若有选中节点则 `store.selectNode(null)`（避免单节点编辑器覆盖多选面板）
- 侧栏：`store.selectedNodeIds.length > 0` 时显示「已选 N 节点」面板（替代原 ConceptEditor/ConceptList 区域）：列出选中节点名 + 「取消选择」+「批量删除」按钮
- 批量删除：`Promise.all(store.selectedNodeIds.map(slug => editor.removeConcept(paperId, slug, oldNode)))`，成功后 `store.clearMultiSelect()` + `reload()`
- 视图切换或离开时 `clearMultiSelect()`

- [ ] **Step 4: 验证 + 提交**

`npm run build` + `npm test` 通过；手动逻辑自检（无法自动验证 D3 交互，仔细读代码确保 drag/zoom/框选不互相破坏）。
```bash
git add frontend/src/components/KnowledgeGraph.vue frontend/src/views/WorkbenchView.vue
git commit -m "feat(workbench): 编辑模式框选 + 多选批量移动/删除"
```

---

### Task 5: 全局回归 + 收尾

**Files:** 无新增

- [ ] **Step 1: 全量验证**

- `cd frontend && npm test` 全部通过
- `npm run build` 通过
- 逐项自查（读代码核对，无法自动验证的列"待人工"）：
  - [ ] 图例点击过滤生效/取消，布局不跳
  - [ ] 搜索定位聚焦节点
  - [ ] 编辑模式空白框选 → 多选面板 → 批量删除
  - [ ] 多选后普通模式拖动整组移动
  - [ ] 回归：单节点拖拽建关系、撤销重做、导出、ViewSwitcher、Workbench 图谱渲染

- [ ] **Step 2: 提交收尾**

```bash
git add -A
git commit -m "chore: SP2 图谱交互增强完成——过滤/搜索定位/多选框选"
```

---

## Self-Review（自查）

**1. Spec 覆盖：** F1（Task 2）✓、F2（Task 3）✓、F3（Task 4）✓、store 状态（Task 1）✓、验收映射到 Task 5。**2. 占位符：** 无 TBD；D3 交互细节以行为规格给出（框选坐标、拖拽裁决在 Task 4 明确）。**3. 类型一致：** store actions 名统一（toggleFilter/toggleMultiSelect/setSelectedNodes），expose `zoomToNode` 在 Task 3 定义、Task 3 Step 2 使用，一致。
