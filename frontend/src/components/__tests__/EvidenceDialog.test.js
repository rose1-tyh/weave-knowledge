import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import EvidenceDialog from '../EvidenceDialog.vue'
import * as api from '@/api'

vi.mock('@/api', () => ({ evidenceContext: vi.fn() }))

// el-dialog 默认 teleport 到 body，wrapper.find 找不到内容 → 用 stub 内联渲染 slot
const stubs = { 'el-dialog': { template: '<div class="ev-dialog-stub"><slot /></div>' } }
const opts = { global: { stubs } }

describe('EvidenceDialog', () => {
  beforeEach(() => { api.evidenceContext.mockReset() })

  it('打开后展示上下文与页码，证据串高亮', async () => {
    // context = "前文 图谱是知识结构 后文"，start=3/end=10 → 高亮"图谱是知识结构"
    api.evidenceContext.mockResolvedValue({
      found: true, context: '前文 图谱是知识结构 后文', start: 3, end: 10, page: 2,
    })
    const wrapper = mount(EvidenceDialog, { props: { paperId: 'p1' }, ...opts })
    wrapper.vm.open('图谱是知识结构')
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('第 2 页')
    expect(wrapper.find('.ev-hit').text()).toBe('图谱是知识结构')
  })

  it('找不到证据时显示原因', async () => {
    api.evidenceContext.mockResolvedValue({ found: false, reason: '未找到证据串' })
    const wrapper = mount(EvidenceDialog, { props: { paperId: 'p1' }, ...opts })
    wrapper.vm.open('不存在')
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('未找到证据串')
  })
})
