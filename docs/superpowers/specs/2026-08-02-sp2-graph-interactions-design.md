# SP2 图谱交互增强 设计

- 日期：2026-08-02
- 状态：已批准（用户确认）
- 目标：让图谱从"能看"到"好用"——过滤、聚焦、批量操作

## 功能范围（用户选定三项）

### F1 类型过滤 + 图例交互
- 图例「概念」区类型项可点击，点击切换过滤（再次点击取消），激活项高亮
- 过滤时：非该类型节点淡出（opacity 0.12，保留空间上下文），两端都不匹配的连线淡出（opacity 0.05）
- **不重排布局**：只改 opacity，不重跑力模拟
- 过滤状态存 graph store（`filterType`），Workbench/Explore 共享

### F2 图谱内搜索定位
- 工作台顶部加搜索框，输入即匹配概念名，下拉展示候选
- 选中 → KnowledgeGraph `zoomToNode(id)` 居中放大 + 高亮 + 侧栏显示详情（复用现有选中）
- 搜索匹配来源：store.graphData.nodes 按 name includes

### F3 多选 / 框选（编辑模式）
- 编辑模式下拖空白处框选 → 选中框内所有节点；此模式下背景拖拽不平移（滚轮/按钮缩放）
- 多选后：拖动任一选中节点 → 全部一起移动（复用 d3 drag，共享位移）
- 侧栏显示「已选 N 节点」面板 + 批量删除按钮（逐个调 deleteConcept API）
- 多选状态存 graph store（`selectedNodeIds` 数组）

## 技术要点
- 改动集中在 `KnowledgeGraph.vue` + `WorkbenchView.vue`，graph store 加状态与 actions
- 动效只用 transform/opacity
- 不破坏：单节点拖拽建关系、撤销/重做、导出、视图切换、编辑功能
- KnowledgeGraph 新增 expose：`zoomToNode(id)`

## 验收
- 图例点击过滤生效，再点恢复，布局不跳
- 搜索定位到节点并聚焦
- 编辑模式框选多节点，拖动联动移动，批量删除成功
- 既有功能回归无破坏；`npm test`、`npm run build` 通过
