import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'

// 节点/链接数据：与 Workbench 图谱数据同构（含 status/confidence 字段）
const nodes3 = [
  { id: 'a', name: '甲', definition: '', type: 'method', color: '#e8453c', page: 1, status: 'pending', confidence: 0.5 },
  { id: 'b', name: '乙', definition: '', type: 'theory', color: '#8b5cf6', page: 1, status: 'pending', confidence: 0.5 },
  { id: 'c', name: '丙', definition: '', type: 'finding', color: '#f59e0b', page: 1, status: 'pending', confidence: 0.5 },
]
const links2 = [
  { source: 'a', target: 'b', type: 'cites', color: '#6b7280', status: 'pending', confidence: 0.5 },
  { source: 'b', target: 'c', type: 'supports', color: '#10b981', status: 'pending', confidence: 0.5 },
]
const nodes5 = [
  ...nodes3,
  { id: 'd', name: '丁', definition: '', type: 'tool', color: '#00d4ff', page: 1, status: 'pending', confidence: 0.5 },
  { id: 'e', name: '戊', definition: '', type: 'dataset', color: '#10b981', page: 1, status: 'pending', confidence: 0.5 },
]

function mountGraph(data) {
  return mount(KnowledgeGraph, {
    props: { data, selectedId: null, editing: false },
    global: { plugins: [createPinia()] },
    attachTo: document.body,
  })
}

describe('KnowledgeGraph 渲染', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('mount 渲染全部节点与链接', () => {
    const w = mountGraph({ nodes: nodes3, links: links2 })
    expect(w.findAll('[data-role="node"]').length).toBe(3)
    expect(w.findAll('line[data-role="link"]').length).toBe(2)
    w.unmount()
  })

  it('数据更新后节点 join 正确且复用原 DOM（增量渲染，不重建）', async () => {
    const w = mountGraph({ nodes: nodes3, links: links2 })
    const firstGroup = w.findAll('[data-role="node"]')[0].element
    const secondGroup = w.findAll('[data-role="node"]')[1].element

    await w.setProps({ data: { nodes: nodes5, links: links2 } })
    const groups = w.findAll('[data-role="node"]')
    expect(groups.length).toBe(5)
    // 原有节点 DOM 应被复用而非重建
    expect(groups[0].element).toBe(firstGroup)
    expect(groups[1].element).toBe(secondGroup)
    // 新增节点渲染出文本
    expect(w.text()).toContain('丁')
    w.unmount()
  })

  it('数据更新移除节点后 exit 正确', async () => {
    const w = mountGraph({ nodes: nodes5, links: links2 })
    expect(w.findAll('[data-role="node"]').length).toBe(5)
    await w.setProps({ data: { nodes: nodes3, links: links2 } })
    expect(w.findAll('[data-role="node"]').length).toBe(3)
    w.unmount()
  })

  it('编辑模式切换不抛错', async () => {
    const w = mountGraph({ nodes: nodes3, links: links2 })
    await w.setProps({ editing: true })
    await w.setProps({ editing: false })
    expect(w.findAll('[data-role="node"]').length).toBe(3)
    w.unmount()
  })

  it('空数据不渲染节点', () => {
    const w = mountGraph({ nodes: [], links: [] })
    expect(w.findAll('[data-role="node"]').length).toBe(0)
    w.unmount()
  })
})
