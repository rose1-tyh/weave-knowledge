<template>
  <div class="explore-page">
    <ParticleBackground :accent="'#a78bfa'" :density="60" :opacity="0.4" />

    <div class="explore-sidebar">
      <h3>选择论文</h3>
      <p class="explore-hint">合并多篇论文生成融合知识图谱</p>
      <div class="paper-select-list" v-if="papers.length">
        <label v-for="p in papers" :key="p.id" class="paper-checkbox">
          <input type="checkbox" :value="p.id" v-model="selectedIds" />
          <span>{{ p.title }}</span>
        </label>
      </div>
      <p v-else class="no-papers">暂无论文</p>
      <el-button type="primary" @click="generateFusion" :disabled="selectedIds.length < 2" style="width:100%;margin-top:16px">
        生成融合图谱
      </el-button>
    </div>

    <div class="explore-main">
      <div v-if="loading" class="explore-loading">分析中...</div>
      <div v-else-if="!fusionData" class="explore-empty">
        <p>选择 2 篇以上论文，生成跨论文知识融合图谱</p>
        <p class="explore-empty-hint">⌘K 全局搜索所有概念</p>
      </div>
      <KnowledgeGraph v-else :data="fusionData" @select-node="onSelectNode" />
    </div>

    <div class="explore-right" v-if="searchResults.length || selectedNode">
      <GlobalSearch v-if="!selectedNode" :results="searchResults" @search="doSearch" @select="onSelectResult" />
      <ConceptEditor v-else :concept="selectedNode" :editing="false" @close="selectedNode = null" />
    </div>

    <p v-if="loadError" class="explore-load-error">{{ loadError }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLibraryStore } from '@/stores/library'
import { fusionGraph, searchConcepts } from '@/api'
import { useApiError } from '@/composables/useApiError'
import { computePaperIndex } from '@/utils/fusion'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import ConceptEditor from '@/components/ConceptEditor.vue'
import GlobalSearch from '@/components/GlobalSearch.vue'
import ParticleBackground from '@/components/ParticleBackground.vue'

const router = useRouter()
const lib = useLibraryStore()
const { showError } = useApiError()
const papers = ref([])
const selectedIds = ref([])
const fusionData = ref(null)
const loading = ref(false)
const selectedNode = ref(null)
const searchResults = ref([])
const loadError = ref('')

onMounted(async () => {
  try {
    await lib.fetchPapers()
  } catch (e) {
    loadError.value = e.message || '论文列表加载失败'
    showError(e)
  }
  papers.value = lib.papers.filter(p => p.extract_status === 'done')
})

async function generateFusion() {
  if (selectedIds.value.length < 2) return
  loading.value = true
  try {
    const data = await fusionGraph(selectedIds.value)
    if (data) {
      // 融合来源着色：给每个节点附 paperIndex（单来源→论文序号；多来源→-1 混合色）
      const selected = selectedIds.value
      data.nodes = (data.nodes || []).map(n => ({
        ...n,
        paperIndex: computePaperIndex(n.paperIds, selected),
      }))
    }
    fusionData.value = data
  } catch (e) {
    showError(e, '融合图谱生成失败')
  }
  loading.value = false
}

async function doSearch(q) {
  if (!q) { searchResults.value = []; return }
  try {
    const data = await searchConcepts(q)
    searchResults.value = data.results || []
  } catch (e) {
    showError(e, '搜索失败')
  }
}

function onSelectNode(id) {
  if (!fusionData.value) return
  selectedNode.value = fusionData.value.nodes.find(n => n.id === id) || null
}

// 点击搜索结果 → 跳转该概念所属论文的工作台
function onSelectResult(r) {
  searchOpen.value = false
  selectedNode.value = null
  const paperId = r?.paperId
  if (paperId) {
    router.push({ name: 'Workbench', params: { paperId } })
  }
}
</script>

<style scoped>
.explore-page {
  --page-accent: var(--page-explore-accent);
  position: relative;
  display: flex;
  height: 100%;
  overflow: hidden;
  background:
    radial-gradient(circle at 70% 20%, rgba(139, 92, 246, 0.4), transparent 50%),
    radial-gradient(circle at 8% 92%, rgba(167, 139, 250, 0.16), transparent 42%),
    var(--space-deep);
}
.explore-page::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background-image: var(--grain-overlay);
}
.explore-sidebar {
  position: relative;
  z-index: 2;
  width: 280px;
  flex-shrink: 0;
  padding: var(--space-lg);
  border-right: 1px solid var(--border-subtle);
  overflow-y: auto;
}
.explore-sidebar h3 { font-family: var(--font-display); color: var(--text-primary); margin-bottom: var(--space-xs); }
.explore-hint { font-size: var(--text-sm); color: var(--text-muted); margin-bottom: var(--space-md); }
.paper-checkbox { display: flex; align-items: flex-start; gap: var(--space-sm); padding: var(--space-sm) 0; cursor: pointer; font-size: var(--text-sm); color: var(--text-secondary); }
.paper-checkbox input[type=checkbox] { margin-top: 2px; accent-color: var(--vermilion); }
.no-papers { color: var(--text-muted); font-size: var(--text-sm); padding: var(--space-md) 0; }
.explore-main { position: relative; z-index: 2; flex: 1; min-width: 0; }
.explore-loading, .explore-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); gap: var(--space-sm); }
.explore-empty-hint { font-size: var(--text-xs); color: var(--text-disabled); }
.explore-right { position: relative; z-index: 2; width: 300px; flex-shrink: 0; border-left: 1px solid var(--border-subtle); overflow-y: auto; }

.explore-load-error {
  position: absolute;
  z-index: 2;
  top: var(--space-md);
  right: var(--space-md);
  color: var(--vermilion);
  font-size: var(--text-sm);
}
</style>
