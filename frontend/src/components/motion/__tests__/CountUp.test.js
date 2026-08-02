import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import CountUp from '../CountUp.vue'

describe('CountUp', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('从 0 滚动到目标值并格式化', async () => {
    const wrapper = mount(CountUp, { props: { value: 1280 } })
    // 跳过完整动画，直接把内部值推到终点
    wrapper.vm.current = 1280
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toBe('1,280')
  })
})
