import { describe, it, expect } from 'vitest'
import { computePaperIndex, nodeStroke, paperPalette, MIXED_SOURCE_STROKE } from '@/utils/fusion'

describe('computePaperIndex（融合来源 → 论文序号）', () => {
  const selected = ['paper-a', 'paper-b', 'paper-c']

  it('单来源且命中选中列表 → 返回对应论文序号', () => {
    expect(computePaperIndex(['paper-b'], selected)).toBe(1)
    expect(computePaperIndex(['paper-c'], selected)).toBe(2)
  })

  it('单来源但不在选中列表 → 兜底为 0', () => {
    expect(computePaperIndex(['ghost'], selected)).toBe(0)
  })

  it('多来源 → -1（混合色）', () => {
    expect(computePaperIndex(['paper-a', 'paper-b'], selected)).toBe(-1)
  })

  it('空数组 / 非数组 / 缺省 → -1', () => {
    expect(computePaperIndex([], selected)).toBe(-1)
    expect(computePaperIndex(undefined, selected)).toBe(-1)
    expect(computePaperIndex(null, selected)).toBe(-1)
  })
})

describe('nodeStroke（融合节点描边着色）', () => {
  it('paperIndex 单来源 → 论文序号对应调色板色', () => {
    expect(nodeStroke({ paperIndex: 0 })).toBe(paperPalette[0])
    expect(nodeStroke({ paperIndex: 2 })).toBe(paperPalette[2])
  })

  it('paperIndex 超过调色板长度 → 取模循环', () => {
    expect(nodeStroke({ paperIndex: 5 })).toBe(paperPalette[0])
  })

  it('paperIndex = -1（多来源混合）→ 混合亮紫色', () => {
    expect(nodeStroke({ paperIndex: -1 })).toBe(MIXED_SOURCE_STROKE)
  })

  it('无 paperIndex（非融合图谱）→ 走概念类型色', () => {
    expect(nodeStroke({ color: '#8b5cf6' })).toBe('#8b5cf6')
    expect(nodeStroke({})).toBe('rgba(255,255,255,0.35)')
    expect(nodeStroke(null)).toBe('rgba(255,255,255,0.35)')
  })
})
