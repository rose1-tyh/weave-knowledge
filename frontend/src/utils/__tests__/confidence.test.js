import { describe, it, expect } from 'vitest'
import { isLowConfidence, nodeStatusVisual, statusLabel, confPercent } from '@/utils/confidence'

describe('confidence utils', () => {
  it('isLowConfidence 阈值', () => {
    expect(isLowConfidence(0.5)).toBe(true)
    expect(isLowConfidence(0.6)).toBe(false)
    expect(isLowConfidence(undefined)).toBe(false)
  })

  it('已确认节点盖印章、不虚化', () => {
    const v = nodeStatusVisual({ status: 'confirmed', confidence: 0.5 })
    expect(v.seal).toBe(true)
    expect(v.dashed).toBe(false)
    expect(v.opacity).toBe(1)
  })

  it('未确认低置信 → 虚线 + 明显虚化', () => {
    const v = nodeStatusVisual({ status: 'pending', confidence: 0.4 })
    expect(v.seal).toBe(false)
    expect(v.dashed).toBe(true)
    expect(v.opacity).toBeLessThan(0.7)
  })

  it('未确认高置信 → 虚线但轻度虚化', () => {
    const v = nodeStatusVisual({ status: 'pending', confidence: 0.9 })
    expect(v.dashed).toBe(true)
    expect(v.opacity).toBeGreaterThan(0.7)
  })

  it('无信任字段（融合/旧数据）→ 中性：不盖章、不虚、全不透明', () => {
    const v = nodeStatusVisual({ name: 'x' })
    expect(v).toEqual({ seal: false, dashed: false, opacity: 1 })
    expect(nodeStatusVisual(null)).toEqual({ seal: false, dashed: false, opacity: 1 })
  })

  it('状态与置信度文案', () => {
    expect(statusLabel('confirmed')).toBe('已确认')
    expect(statusLabel(undefined)).toBe('待确认')
    expect(confPercent(0.55)).toBe('55%')
    expect(confPercent(undefined)).toBe('—')
  })
})
