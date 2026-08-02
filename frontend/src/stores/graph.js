import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { extractKnowledge, getGraphData, getPaperInfo } from '@/api'

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
    loading.value = true
    error.value = ''
    try {
      const data = await extractKnowledge(paperId)
      graphData.value = data
    } catch (e) {
      error.value = e.message || '提取失败'
    } finally {
      loading.value = false
    }
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

  return {
    paperTitle, graphData, selectedNodeId, selectedLinkIndex,
    selectedNode, selectedLink, loading, error,
    loadGraph, runExtraction, selectNode, selectLink, clearSelection,
    filterType, selectedNodeIds,
    toggleFilter, setFilter, toggleMultiSelect, clearMultiSelect, setSelectedNodes,
  }
})
