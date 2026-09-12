import { describe, it, expect } from 'vitest'
import { donutSlice, buildDonutSlices, barWidth } from '../charts'

describe('donutSlice', () => {
  it('生成合法弧路径（起止点在半径上）', () => {
    const d = donutSlice(100, 100, 50, 80, 0, 90)
    expect(d).toMatch(/^M/)
    expect(d).toContain('A80,80')
    expect(d).toContain('A50,50')
    // large-arc flag = 0（90° < 180°）
    expect(d).toContain(' 0 0 1 ')
  })

  it('超过 180° 时 large-arc 置 1', () => {
    const d = donutSlice(100, 100, 50, 80, 0, 270)
    expect(d).toContain(' 0 1 1 ')
  })

  it('全圆拆为两段半圆（不退化）', () => {
    const d = donutSlice(100, 100, 50, 80, 0, 360)
    // 两段 arc 外弧 + 两段 arc 内弧
    expect(d.match(/A80,80/g)).toHaveLength(2)
    expect(d.match(/A50,50/g)).toHaveLength(2)
  })
})

describe('buildDonutSlices', () => {
  const counts = [
    { type: 'method', label: '研究方法', value: 3, color: '#e8453c' },
    { type: 'theory', label: '理论基础', value: 1, color: '#8b5cf6' },
  ]

  it('切片角度与计数成比例，带百分比', () => {
    const slices = buildDonutSlices(counts)
    expect(slices).toHaveLength(2)
    expect(slices[0].percent).toBeCloseTo(0.75)
    // method 切片跨度约为 theory 的 3 倍（含等量 pad）
    const sweepA = slices[0].a1 - slices[0].a0
    const sweepB = slices[1].a1 - slices[1].a0
    expect(sweepA / sweepB).toBeCloseTo(3, 1)
  })

  it('空计数返回空数组', () => {
    expect(buildDonutSlices([])).toEqual([])
    expect(buildDonutSlices([{ type: 'x', label: 'x', value: 0 }])).toEqual([])
  })
})

describe('barWidth', () => {
  it('等比缩放并保证最小可见宽度', () => {
    expect(barWidth(50, 100, 200)).toBe(100)
    expect(barWidth(0, 100, 200)).toBe(0)
    expect(barWidth(1, 1000, 200)).toBe(2) // 最小 2
    expect(barWidth(10, 0, 200)).toBe(0)   // max=0 防除零
  })
})
