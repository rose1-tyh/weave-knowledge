import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import WeaveExtraction from '../WeaveExtraction.vue'

describe('WeaveExtraction', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('阶段顺序推进并最终到达成图', async () => {
    const wrapper = mount(WeaveExtraction)
    const t0 = wrapper.vm.stage
    await vi.advanceTimersByTimeAsync(4000)
    expect(wrapper.vm.stage).toBe(3) // 成图
    expect(t0).toBe(0)
  })

  it('超过末阶段不崩溃并停在末尾', async () => {
    const wrapper = mount(WeaveExtraction)
    await vi.advanceTimersByTimeAsync(5000)
    // 不抛异常（末阶段索引越界曾触发 TypeError）
    expect(wrapper.vm.stage).toBe(3) // 停在末阶段，不再增长
    expect(wrapper.text()).toContain('编织成图') // 阶段标签不变
  })
})
