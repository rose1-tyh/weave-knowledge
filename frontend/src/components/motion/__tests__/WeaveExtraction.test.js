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
})
