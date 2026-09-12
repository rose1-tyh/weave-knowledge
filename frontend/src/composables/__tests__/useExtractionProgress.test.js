import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { useExtractionProgress, STAGE_LABELS } from '../useExtractionProgress'
import { getExtractStatus } from '@/api'

vi.mock('@/api', () => ({ getExtractStatus: vi.fn() }))

class FakeEventSource {
  static instances = []
  constructor(url) {
    this.url = url
    this.onmessage = null
    this.onerror = null
    this.closed = false
    FakeEventSource.instances.push(this)
  }
  close() { this.closed = true }
  emit(data) { this.onmessage?.({ data: JSON.stringify(data) }) }
  fail() { this.onerror?.(new Error('connection lost')) }
}

// composable 内部使用 onUnmounted → 挂载宿主组件提供实例上下文
function withHost(setup) {
  let result
  const Host = defineComponent({
    setup() {
      result = setup()
      return () => h('div')
    },
  })
  mount(Host)
  return result
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
  vi.useFakeTimers()
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('useExtractionProgress', () => {
  it('SSE 快照驱动状态与百分比，终态后关闭连接', async () => {
    const onDone = vi.fn()
    const { snapshot, percent, stageLabel, start } = withHost(() => useExtractionProgress())

    start('p1', { onDone })
    expect(FakeEventSource.instances).toHaveLength(1)
    const es = FakeEventSource.instances[0]
    expect(es.url).toBe('/api/extract/progress/p1')

    es.emit({ status: 'processing', stage: 'extracting', progress: 0.5, detail: '2/4', message: 'AI 提取中（2/4）', error: '' })
    expect(snapshot.value.status).toBe('processing')
    expect(snapshot.value.stage).toBe('extracting')
    expect(percent.value).toBe(50)
    expect(stageLabel.value).toBe(STAGE_LABELS.extracting)
    expect(onDone).not.toHaveBeenCalled()
    expect(es.closed).toBe(false)

    es.emit({ status: 'done', stage: 'done', progress: 1, detail: '', message: '提取完成', error: '' })
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(es.closed).toBe(true)
  })

  it('SSE 断连且非终态 → 自动降级轮询', async () => {
    getExtractStatus.mockResolvedValue({ status: 'processing', stage: 'graphing', progress: 0.96 })
    const { snapshot, start } = withHost(() => useExtractionProgress())

    start('p2', {})
    const es = FakeEventSource.instances[0]
    es.emit({ status: 'processing', stage: 'extracting', progress: 0.3 })
    es.fail()   // 断连

    await vi.advanceTimersByTimeAsync(2100)
    expect(getExtractStatus).toHaveBeenCalledWith('p2')
    expect(snapshot.value.stage).toBe('graphing')
  })

  it('无 EventSource 环境 → 直接轮询，failed 触发 onFailed', async () => {
    vi.stubGlobal('EventSource', undefined)
    getExtractStatus
      .mockResolvedValueOnce({ status: 'processing', stage: 'parsing', progress: 0.08 })
      .mockResolvedValue({ status: 'failed', stage: 'failed', progress: 0.3, error: 'AI 服务不可用' })
    const onFailed = vi.fn()
    const { snapshot, start } = withHost(() => useExtractionProgress())

    start('p3', { onFailed })
    await vi.advanceTimersByTimeAsync(4500)
    expect(onFailed).toHaveBeenCalledTimes(1)
    expect(snapshot.value.error).toBe('AI 服务不可用')
  })
})
