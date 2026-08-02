<template>
  <div class="explore-page">
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
      </div>
      <KnowledgeGraph v-else :data="fusionData" @select-node="onSelectNode" />
    </div>
    <div class="explore-right" v-if="searchResults.length || selectedNode">
      <GlobalSearch v-if="!selectedNode" :results="searchResults" @search="doSearch" />
      <ConceptEditor v-else :concept="selectedNode" :editing="false" @close="selectedNode = null" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useLibraryStore } from '@/stores/library'
import { fusionGraph, searchConcepts } from '@/api'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import ConceptEditor from '@/components/ConceptEditor.vue'
import GlobalSearch from '@/components/GlobalSearch.vue'

const lib = useLibraryStore()
const papers = ref([])
const selectedIds = ref([])
const fusionData = ref(null)
const loading = ref(false)
const selectedNode = ref(null)
const searchResults = ref([])

onMounted(async () => {
  await lib.fetchPapers()
  papers.value = lib.papers.filter(p => p.extract_status === 'done')
})

async function generateFusion() {
  if (selectedIds.value.length < 2) return
  loading.value = true
  try {
    fusionData.value = await fusionGraph(selectedIds.value)
  } catch (_) {}
  loading.value = false
}

async function doSearch(q) {
  if (!q) { searchResults.value = []; return }
  try {
    const data = await searchConcepts(q)
    searchResults.value = data.results || []
  } catch (_) {}
}

function onSelectNode(id) {
  if (!fusionData.value) return
  selectedNode.value = fusionData.value.nodes.find(n => n.id === id) || null
}
</script>

<style scoped>
.explore-page { --page-accent: var(--page-explore-accent); display: flex; height: 100%; }
.explore-sidebar { width: 280px; flex-shrink: 0; padding: var(--space-lg); border-right: 1px solid var(--border-subtle); overflow-y: auto; }
.explore-sidebar h3 { font-family: var(--font-display); color: var(--text-primary); margin-bottom: var(--space-xs); }
.explore-hint { font-size: var(--text-sm); color: var(--text-muted); margin-bottom: var(--space-md); }
.paper-checkbox { display: flex; align-items: flex-start; gap: var(--space-sm); padding: var(--space-sm) 0; cursor: pointer; font-size: var(--text-sm); color: var(--text-secondary); }
.paper-checkbox input[type=checkbox] { margin-top: 2px; accent-color: var(--vermilion); }
.no-papers { color: var(--text-muted); font-size: var(--text-sm); padding: var(--space-md) 0; }
.explore-main { flex: 1; position: relative; min-width: 0; }
.explore-loading, .explore-empty { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); }
.explore-right { width: 300px; flex-shrink: 0; border-left: 1px solid var(--border-subtle); overflow-y: auto; }
</style>
