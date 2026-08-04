import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConceptEditor from '../ConceptEditor.vue'

const baseConcept = {
  id: 'abc', name: '图谱', definition: '知识结构', type: 'finding', page: 2,
  evidence: '图谱是知识结构', confidence: 0.55, status: 'pending',
}

// stub Element Plus 按钮：attrs（含 data-test）透传到根元素，避免组件未注册告警
const stubs = { 'el-button': { template: '<button><slot /></button>' } }
const opts = { global: { stubs } }

describe('ConceptEditor 只读模式', () => {
  it('显示状态徽章、置信度与低置信提示', () => {
    const wrapper = mount(ConceptEditor, { props: { concept: baseConcept, editing: false }, ...opts })
    expect(wrapper.text()).toContain('待确认')
    expect(wrapper.text()).toContain('55%')
    expect(wrapper.text()).toContain('建议人工确认')
    expect(wrapper.text()).toContain('图谱是知识结构')
  })

  it('点击确认/驳回触发事件', async () => {
    const wrapper = mount(ConceptEditor, { props: { concept: baseConcept, editing: false }, ...opts })
    await wrapper.find('[data-test="confirm"]').trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
    await wrapper.find('[data-test="reject"]').trigger('click')
    expect(wrapper.emitted('reject')).toBeTruthy()
  })

  it('已确认概念显示印章文案、不显示确认按钮', () => {
    const wrapper = mount(ConceptEditor, { props: { concept: { ...baseConcept, status: 'confirmed' }, editing: false }, ...opts })
    expect(wrapper.text()).toContain('已确认')
    expect(wrapper.find('[data-test="confirm"]').exists()).toBe(false)
  })
})
