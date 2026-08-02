import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGraphStore } from '../graph'

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
})
