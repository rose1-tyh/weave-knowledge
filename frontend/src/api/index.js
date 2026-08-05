import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000,
})

api.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body.code === 200) return body.data
    return Promise.reject(new Error(body.msg || '请求失败'))
  },
  (err) => {
    const msg = err.response?.data?.detail || err.message || '网络错误'
    return Promise.reject(new Error(msg))
  }
)

// ── 上传 ──
export function uploadPaper(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ── 文本/URL/手动创建 ──
export function extractFromText(title, text) { return api.post('/extract-text', { title, text }) }
export function extractFromUrl(url) { return api.post('/extract-url', { url }) }
export function createEmptyPaper(title) { return api.post('/papers/create-empty', { title }) }

// ── 论文管理 ──
export function getPapers(params) { return api.get('/library/papers', { params }) }
export function getPaperInfo(paperId) { return api.get(`/paper/${paperId}`) }
export function deletePaper(paperId) { return api.delete(`/library/papers/${paperId}`) }
export function updatePaper(paperId, data) { return api.patch(`/library/papers/${paperId}`, data) }

// ── 图谱数据 ──
export function extractKnowledge(paperId) { return api.post('/extract', { paper_id: paperId }) }
export function getExtractStatus(paperId) { return api.get(`/extract-status/${paperId}`) }
export function getGraphData(paperId) { return api.get(`/graph/${paperId}`) }

// ── 知识编辑（概念） ──
export function addConcept(paperId, data) { return api.post(`/graph/${paperId}/concepts`, data) }
export function updateConcept(paperId, slug, data) { return api.put(`/graph/${paperId}/concepts/${slug}`, data) }
export function deleteConcept(paperId, slug) { return api.delete(`/graph/${paperId}/concepts/${slug}`) }

// ── 知识编辑（关系） ──
export function addRelation(paperId, data) { return api.post(`/graph/${paperId}/relations`, data) }
export function updateRelation(paperId, id, data) { return api.put(`/graph/${paperId}/relations/${id}`, data) }
export function deleteRelation(paperId, id) { return api.delete(`/graph/${paperId}/relations/${id}`) }

// ── 可信抽取 ──
export function evidenceContext(paperId, evidence) {
  return api.post(`/papers/${paperId}/evidence-context`, { evidence })
}
export function backfillConfidence(paperId) {
  return api.post('/system/backfill-confidence', null, { params: paperId ? { paper_id: paperId } : {} })
}

// ── 全局探索 ──
export function fusionGraph(paperIds) { return api.post('/explore/fusion', { paper_ids: paperIds }) }
export function searchConcepts(query) { return api.get('/explore/search', { params: { q: query } }) }
export function suggestMerges(paperIds) { return api.post('/explore/merge-suggestions', { paper_ids: paperIds }) }

// ── 导出 ──
export function exportJSON(paperId) { return api.get(`/export/${paperId}/json`) }
export function exportMarkdown(paperId) { return api.get(`/export/${paperId}/markdown`) }

// ── 统计 ──
export function getStats() { return api.get('/stats') }

export default api
