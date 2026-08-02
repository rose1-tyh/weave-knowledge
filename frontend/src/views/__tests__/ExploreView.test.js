import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

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

function key(type, init) {
  window.dispatchEvent(new KeyboardEvent(type, init))
}

const mountExplore = () => mount(ExploreView, {
  global: { stubs: { 'el-button': { template: '<button><slot /></button>' } } },
})

describe('ExploreView ⌘K 全局搜索面板', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初始面板关闭', async () => {
    const wrapper = mountExplore()
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.searchOpen).toBe(false)
  })

  it('Ctrl+K 打开，Esc 关闭', async () => {
    const wrapper = mountExplore()
    await wrapper.vm.$nextTick()

    key('keydown', { key: 'k', ctrlKey: true, code: 'KeyK' })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.searchOpen).toBe(true)

    key('keydown', { key: 'Escape', code: 'Escape' })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.searchOpen).toBe(false)
  })

  it('Meta+K 再次触发会关闭已打开的面板', async () => {
    const wrapper = mountExplore()
    await wrapper.vm.$nextTick()

    key('keydown', { key: 'K', metaKey: true, code: 'KeyK' })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.searchOpen).toBe(true)

    key('keydown', { key: 'k', metaKey: true, code: 'KeyK' })
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.searchOpen).toBe(false)
  })
})
