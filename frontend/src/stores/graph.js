import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { extractKnowledge, getExtractStatus, getGraphData, getPaperInfo } from '@/api'

export const useGraphStore = defineStore('graph', () => {
  const paperTitle = ref('')
  const graphData = ref(null)       // { nodes, links, paperTitle }
  const selectedNodeId = ref(null)
  const selectedLinkIndex = ref(null)
  const loading = ref(false)
  const error = ref('')

  const selectedNode = computed(() => {
    if (!selectedNodeId.value || !graphData.value) return null
    return graphData.value.nodes.find(n => n.id === selectedNodeId.value) || null
  })

  const selectedLink = computed(() => {
    if (selectedLinkIndex.value === null || !graphData.value) return null
    return graphData.value.links[selectedLinkIndex.value] || null
  })

  async function loadGraph(paperId) {
    loading.value = true
    error.value = ''
    try {
      const info = await getPaperInfo(paperId)
      paperTitle.value = info.title
      const data = await getGraphData(paperId)
      graphData.value = data
    } catch (e) {
      error.value = e.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function runExtraction(paperId) {
    // 提交后台提取任务，立即返回（服务端异步执行，进度经 getExtractStatus 轮询）
    loading.value = true
    error.value = ''
    try {
      await extractKnowledge(paperId)
    } catch (e) {
      error.value = e.message || '提取失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  // 确保论文已提取：检查状态 → 必要时提交 → 轮询到 done/failed
  async function ensureExtracted(paperId) {
    try {
      const info = await getPaperInfo(paperId)
      const st = info.extract_status
      if (st === 'done' && graphData.value?.nodes?.length) return
      if (st !== 'processing') await runExtraction(paperId) // 提交（服务端幂等）
      await pollExtraction(paperId)
    } catch (e) {
      error.value = e.message || '提取失败'
      throw e
    }
  }

  // 轮询提取状态：done → 加载图谱；failed/not_found → 抛错；超时兜底
  async function pollExtraction(paperId, interval = 2000, maxAttempts = 120) {
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(r => setTimeout(r, interval))
      const st = await getExtractStatus(paperId)
      if (st.status === 'done') { await loadGraph(paperId); return }
      if (st.status === 'failed') { throw new Error(st.error || '提取失败') }
      if (st.status === 'not_found') { throw new Error('论文不存在') }
    }
    throw new Error('提取超时，请重试')
  }

  function selectNode(id) { selectedNodeId.value = id; selectedLinkIndex.value = null }
  function selectLink(index) { selectedLinkIndex.value = index; selectedNodeId.value = null }
  function clearSelection() { selectedNodeId.value = null; selectedLinkIndex.value = null }

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

  const filterPending = ref(false)
  function togglePendingFilter() { filterPending.value = !filterPending.value }

  return {
    paperTitle, graphData, selectedNodeId, selectedLinkIndex,
    selectedNode, selectedLink, loading, error,
    loadGraph, runExtraction, ensureExtracted, pollExtraction,
    selectNode, selectLink, clearSelection,
    filterType, selectedNodeIds, filterPending,
    toggleFilter, setFilter, toggleMultiSelect, clearMultiSelect, setSelectedNodes, togglePendingFilter,
  }
})
