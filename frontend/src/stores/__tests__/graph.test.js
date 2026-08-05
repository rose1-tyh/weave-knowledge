import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGraphStore } from '../graph'

vi.mock('@/api', () => ({
  extractKnowledge: vi.fn(),
  getExtractStatus: vi.fn(),
  getGraphData: vi.fn(),
  getPaperInfo: vi.fn(),
}))

import { getExtractStatus, getPaperInfo, extractKnowledge, getGraphData } from '@/api'

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

  it('togglePendingFilter 切换', () => {
    const s = useGraphStore()
    expect(s.filterPending).toBe(false)
    s.togglePendingFilter()
    expect(s.filterPending).toBe(true)
  })
})

describe('graph store 提取轮询状态机', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })
  afterEach(() => vi.useRealTimers())

  it('ensureExtracted: done 且已有图谱 → 不提交不轮询', async () => {
    const s = useGraphStore()
    s.graphData = { nodes: [{ id: 'a' }], links: [] }
    getPaperInfo.mockResolvedValue({ extract_status: 'done' })
    await s.ensureExtracted('p1')
    expect(extractKnowledge).not.toHaveBeenCalled()
    expect(getExtractStatus).not.toHaveBeenCalled()
  })

  it('ensureExtracted: pending → 提交 → 轮询到 done 后加载图谱', async () => {
    const s = useGraphStore()
    getPaperInfo.mockResolvedValue({ extract_status: 'pending', title: 't' })
    extractKnowledge.mockResolvedValue({})
    getGraphData.mockResolvedValue({ paperTitle: 't', nodes: [{ id: 'a' }], links: [] })
    getExtractStatus
      .mockResolvedValueOnce({ status: 'processing' })
      .mockResolvedValueOnce({ status: 'done' })

    const p = s.ensureExtracted('p1')
    await vi.advanceTimersByTimeAsync(2100) // 第一轮轮询：processing
    await vi.advanceTimersByTimeAsync(2100) // 第二轮轮询：done
    await p

    expect(extractKnowledge).toHaveBeenCalledWith('p1')
    expect(s.graphData.nodes).toHaveLength(1)
    expect(s.error).toBe('')
  })

  it('ensureExtracted: processing（刷新恢复）→ 不提交，直接轮询', async () => {
    const s = useGraphStore()
    getPaperInfo.mockResolvedValue({ extract_status: 'processing', title: 't' })
    getGraphData.mockResolvedValue({ paperTitle: 't', nodes: [{ id: 'a' }], links: [] })
    getExtractStatus.mockResolvedValue({ status: 'done' })

    const p = s.ensureExtracted('p1')
    await vi.advanceTimersByTimeAsync(2100)
    await p

    expect(extractKnowledge).not.toHaveBeenCalled()
    expect(s.graphData.nodes).toHaveLength(1)
  })

  it('ensureExtracted: failed → 抛出错误并记录', async () => {
    const s = useGraphStore()
    getPaperInfo.mockResolvedValue({ extract_status: 'pending' })
    extractKnowledge.mockResolvedValue({})
    getExtractStatus.mockResolvedValue({ status: 'failed', error: 'AI 服务不可用' })

    const p = s.ensureExtracted('p1')
    const assertion = expect(p).rejects.toThrow('AI 服务不可用') // 先挂接，避免 unhandled rejection
    await vi.advanceTimersByTimeAsync(2100)
    await assertion
    expect(s.error).toBe('AI 服务不可用')
  })
})
