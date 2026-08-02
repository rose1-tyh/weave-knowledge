<template>
  <div class="workbench" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <div class="wb-loading" v-if="store.loading">
      <div class="loading-dots"><span></span><span></span><span></span></div>
      <p>AI 正在分析论文，提取知识结构...</p>
    </div>
    <div class="wb-error" v-else-if="store.error">
      <p>{{ store.error }}</p>
      <el-button @click="$router.push('/')">返回首页</el-button>
    </div>
    <template v-else-if="store.graphData">
      <div class="wb-main">
        <KnowledgeGraph
          v-if="activeView === 'graph'"
          ref="graphRef"
          :data="store.graphData"
          :selected-id="store.selectedNodeId"
          :editing="editor.isEditing"
          @select-node="onSelectNode"
          @select-link="onSelectLink"
          @add-relation="onAddRelation"
        />
        <TreeView
          v-else-if="activeView === 'tree'"
          :concepts="store.graphData.nodes"
          :selected-id="store.selectedNodeId"
          @select="store.selectNode"
        />
        <MatrixView
          v-else-if="activeView === 'matrix'"
          :concepts="store.graphData.nodes"
          :links="store.graphData.links"
          @select-relation="onSelectRelation"
        />
        <GraphToolbar
          :editing="editor.isEditing"
          :can-undo="editor.canUndo"
          :can-redo="editor.canRedo"
          @zoom-in="graphRef?.zoomBy(1.3)"
          @zoom-out="graphRef?.zoomBy(0.77)"
          @reset="graphRef?.resetZoom()"
          @toggle-edit="editor.toggleEdit"
          @undo="handleUndo"
          @redo="handleRedo"
          @export-png="exportPNG"
          @export-json="exportJSON"
          @export-md="exportMarkdown"
        />
        <ViewSwitcher :active="activeView" @switch="activeView = $event" />
      </div>
      <button
        class="wb-sidebar-toggle"
        :class="{ 'is-collapsed': sidebarCollapsed }"
        :title="sidebarCollapsed ? '展开侧栏' : '折叠侧栏'"
        @click="sidebarCollapsed = !sidebarCollapsed"
      >
        <svg class="wst-chevron" width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <aside class="wb-sidebar" :class="{ 'is-collapsed': sidebarCollapsed }">
        <ConceptEditor
          v-if="store.selectedNode"
          :concept="store.selectedNode"
          :editing="editor.isEditing"
          @save="onSaveConcept"
          @delete="onDeleteConcept"
          @close="store.clearSelection"
        />
        <RelationEditor
          v-else-if="store.selectedLink"
          :link="store.selectedLink"
          :link-index="store.selectedLinkIndex"
          :nodes="store.graphData.nodes"
          :editing="editor.isEditing"
          @save="onSaveRelation"
          @delete="onDeleteRelation"
          @close="store.clearSelection"
        />
        <ConceptEditor
          v-else-if="addingConcept"
          :editing="true"
          @save="onSaveConcept"
          @close="addingConcept = false"
        />
        <ConceptList
          v-else
          :concepts="store.graphData.nodes"
          :selected-id="store.selectedNodeId"
          :editing="editor.isEditing"
          @select="store.selectNode"
          @add="startAddConcept"
        />
      </aside>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useGraphStore } from '@/stores/graph'
import { useEditorStore } from '@/stores/editor'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import GraphToolbar from '@/components/GraphToolbar.vue'
import ViewSwitcher from '@/components/ViewSwitcher.vue'
import ConceptEditor from '@/components/ConceptEditor.vue'
import RelationEditor from '@/components/RelationEditor.vue'
import ConceptList from '@/components/ConceptList.vue'
import TreeView from '@/components/TreeView.vue'
import MatrixView from '@/components/MatrixView.vue'
import { exportJSON as apiExportJSON, exportMarkdown as apiExportMD } from '@/api'
import { toPng } from 'html-to-image'

const route = useRoute()
const router = useRouter()
const store = useGraphStore()
const editor = useEditorStore()
const paperId = route.params.paperId

const activeView = ref('graph')
const graphRef = ref(null)
const addingConcept = ref(false)
const sidebarCollapsed = ref(false)

onMounted(async () => {
  try {
    await store.loadGraph(paperId)
    // if not extracted yet, run extraction
    if (!store.graphData || !store.graphData.nodes?.length) {
      await store.runExtraction(paperId)
    }
  } catch (_) { /* handled by store.error */ }
})

async function reload() {
  try {
    await store.loadGraph(paperId)
  } catch (_) { /* 忽略，store.error 已记录 */ }
}

// ── 图谱选择 ──
function onSelectNode(id) {
  addingConcept.value = false
  store.selectNode(id)
}
function onSelectLink(index) {
  addingConcept.value = false
  if (index === null || index === undefined) store.clearSelection()
  else store.selectLink(index)
}
function onSelectRelation(link) {
  const idx = store.graphData?.links?.indexOf(link)
  if (idx >= 0) store.selectLink(idx)
}

// ── 概念操作 ──
function startAddConcept() {
  store.clearSelection()
  addingConcept.value = true
}
async function onSaveConcept(data) {
  try {
    if (data.slug) {
      await editor.editConcept(paperId, data.slug, data, store.selectedNode)
      ElMessage.success('概念已保存')
    } else {
      const result = await editor.createConcept(paperId, data)
      ElMessage.success('概念已添加')
      addingConcept.value = false
      await reload()
      if (result?.slug) store.selectNode(result.slug)
      return
    }
    await reload()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  }
}
async function onDeleteConcept(slug) {
  const oldConcept = store.selectedNode
  try {
    await editor.removeConcept(paperId, slug, oldConcept)
    store.clearSelection()
    ElMessage.success('概念已删除')
    await reload()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

// ── 关系操作 ──
async function onSaveRelation(data) {
  try {
    await editor.editRelation(paperId, data.relId, data, store.selectedLink)
    ElMessage.success('关系已保存')
    await reload()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  }
}
async function onDeleteRelation(data) {
  const oldLink = store.selectedLink
  try {
    await editor.removeRelation(paperId, data.relId, oldLink)
    store.clearSelection()
    ElMessage.success('关系已删除')
    await reload()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}
async function onAddRelation(data) {
  // KnowledgeGraph 编辑模式拖拽两节点 → 建立关系（默认 cites）
  try {
    await editor.createRelation(paperId, {
      source_slug: data.source,
      target_slug: data.target,
      type: 'cites',
      evidence: '',
    })
    ElMessage.success('关系已创建')
    await reload()
  } catch (e) {
    ElMessage.error(e.message || '创建失败')
  }
}

// ── 撤销/重做 ──
async function handleUndo() {
  try {
    const ok = await editor.undo()
    if (ok) { ElMessage.info('已撤销'); await reload() }
  } catch (e) { ElMessage.error(e.message || '撤销失败') }
}
async function handleRedo() {
  try {
    const ok = await editor.redo()
    if (ok) { ElMessage.info('已重做'); await reload() }
  } catch (e) { ElMessage.error(e.message || '重做失败') }
}

// ── 导出 ──
async function exportPNG() {
  const el = document.querySelector('.wb-main svg')
  if (!el) return
  try {
    const dataUrl = await toPng(el, { backgroundColor: '#080c14' })
    const a = document.createElement('a'); a.href = dataUrl; a.download = 'knowledge-graph.png'; a.click()
  } catch (_) { ElMessage.error('导出失败') }
}
async function exportJSON() {
  try {
    const data = await apiExportJSON(paperId)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'knowledge.json'; a.click()
  } catch (_) { ElMessage.error('导出失败') }
}
async function exportMarkdown() {
  try {
    const data = await apiExportMD(paperId)
    const blob = new Blob([data], { type: 'text/markdown' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'knowledge.md'; a.click()
  } catch (_) { ElMessage.error('导出失败') }
}
</script>

<style scoped>
.workbench { position: relative; display: flex; height: 100%; overflow: hidden; }
.wb-main { flex: 1; position: relative; min-width: 0; }

/* 侧栏折叠按钮：悬浮于图谱右边界，GPU transform 滑动，不动画 width */
.wb-sidebar-toggle {
  position: absolute;
  top: calc(var(--space-md) + 52px);
  right: calc(var(--right-panel-width) + var(--space-md));
  z-index: 20;
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--space-elevated);
  color: var(--text-secondary);
  cursor: pointer;
  transition: transform var(--ease-out-soft), background var(--ease-out), border-color var(--ease-out), color var(--ease-out);
}
.wb-sidebar-toggle:hover { color: var(--text-primary); border-color: var(--border-strong); background: rgba(255,255,255,0.06); }
.wb-sidebar-toggle .wst-chevron { display: block; transition: transform var(--ease-out-soft); }
.workbench.sidebar-collapsed .wb-sidebar-toggle { transform: translateX(var(--right-panel-width)); }
.workbench.sidebar-collapsed .wb-sidebar-toggle .wst-chevron { transform: rotate(180deg); }

/* 侧栏：展开为 flex 项；折叠转 absolute 滑出（transform 动画，宽度变化瞬时） */
.wb-sidebar {
  position: relative;
  flex-shrink: 0;
  border-left: 1px solid var(--border-subtle);
  overflow-y: auto;
  background: var(--space-elevated);
  width: var(--right-panel-width);
  transition: transform var(--ease-out-soft), box-shadow var(--ease-out-soft);
  transform: translateX(0);
}
.wb-sidebar.is-collapsed {
  position: absolute;
  top: 0; right: 0; bottom: 0;
  transform: translateX(100%);
  box-shadow: var(--shadow-elevated);
}
.wb-loading, .wb-error { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-md); color: var(--text-secondary); }
.loading-dots { display: flex; gap: 8px; }
.loading-dots span { width: 10px; height: 10px; border-radius: 50%; background: var(--vermilion); animation: dot-bounce 1.4s ease-in-out infinite both; }
.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }
@keyframes dot-bounce { 0%,80%,100%{transform:scale(0.6);opacity:0.4} 40%{transform:scale(1);opacity:1} }
</style>
