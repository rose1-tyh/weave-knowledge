import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('@/api', () => ({
  fusionGraph: vi.fn(),
  searchConcepts: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('@/stores/library', () => ({
  useLibraryStore: () => ({
    papers: [],
    fetchPapers: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/components/ParticleBackground.vue', () => ({
  default: { name: 'ParticleBackgroundStub', template: '<div class="stub-particle" />' },
}))
vi.mock('@/components/KnowledgeGraph.vue', () => ({
  default: { name: 'KnowledgeGraphStub', template: '<div class="stub-kg" />' },
}))
vi.mock('@/components/ConceptEditor.vue', () => ({
  default: { name: 'ConceptEditorStub', template: '<div class="stub-editor" />' },
}))
vi.mock('@/components/GlobalSearch.vue', () => ({
  default: {
    name: 'GlobalSearchStub',
    props: ['results', 'autofocus'],
    emits: ['search', 'select'],
    template: '<input class="stub-gs-input" @keyup.enter="$emit(\'search\', \'q\')" />',
  },
}))

import ExploreView from '@/views/ExploreView.vue'

const mountExplore = () => mount(ExploreView, {
  global: { stubs: { 'el-button': { template: '<button><slot /></button>' } } },
})

// ⌘K 命令面板已上移至 App.vue 全局（见 App.test.js），此处保留 Explore 页自身行为
describe('ExploreView 全局探索页', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初始无融合图谱、无论文选中', async () => {
    const wrapper = mountExplore()
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.fusionData).toBeNull()
    expect(wrapper.vm.selectedIds).toEqual([])
  })

  it('侧栏概念搜索：结果进入 searchResults', async () => {
    const { searchConcepts } = await import('@/api')
    searchConcepts.mockResolvedValueOnce({ results: [{ id: 'a', name: '概念A' }] })
    const wrapper = mountExplore()
    await wrapper.vm.$nextTick()

    await wrapper.vm.doSearch('概念')
    expect(searchConcepts).toHaveBeenCalledWith('概念')
    expect(wrapper.vm.searchResults).toHaveLength(1)
  })

  it('生成融合图谱：节点附 paperIndex，选中节点更新 selectedNode', async () => {
    const { fusionGraph } = await import('@/api')
    fusionGraph.mockResolvedValueOnce({
      paperTitle: 'X · Y',
      nodes: [{ id: 'n1', name: '概念A', paperIds: ['p2'] }],
      links: [],
    })
    const wrapper = mountExplore()
    await wrapper.vm.$nextTick()

    wrapper.vm.selectedIds = ['p1', 'p2']
    await wrapper.vm.generateFusion()
    expect(wrapper.vm.fusionData).not.toBeNull()
    // 单来源 p2 在所选列表下标 1 → paperIndex=1（computePaperIndex）
    expect(wrapper.vm.fusionData.nodes[0].paperIndex).toBe(1)

    await wrapper.vm.onSelectNode('n1')
    expect(wrapper.vm.selectedNode?.id).toBe('n1')
  })
})
