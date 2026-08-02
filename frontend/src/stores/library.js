import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPapers, deletePaper, getStats } from '@/api'

export const useLibraryStore = defineStore('library', () => {
  const papers = ref([])
  const stats = ref({ paperCount: 0, conceptCount: 0, relationCount: 0 })
  const searchQuery = ref('')
  const sortBy = ref('upload_time')

  const filteredPapers = computed(() => {
    let list = papers.value
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      list = list.filter(p => p.title.toLowerCase().includes(q))
    }
    return list.sort((a, b) => {
      if (sortBy.value === 'upload_time') return b.upload_time.localeCompare(a.upload_time)
      if (sortBy.value === 'title') return a.title.localeCompare(b.title)
      return 0
    })
  })

  async function fetchPapers() {
    const data = await getPapers()
    papers.value = data.papers || []
  }

  async function fetchStats() {
    try {
      stats.value = await getStats()
    } catch (_) { /* ignore */ }
  }

  async function removePaper(id) {
    await deletePaper(id)
    papers.value = papers.value.filter(p => p.id !== id)
    await fetchStats()
  }

  return { papers, stats, searchQuery, sortBy, filteredPapers, fetchPapers, fetchStats, removePaper }
})
