import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

// App 模板用 <router-view> 全局组件：挂载级注册 stub（提供 scoped slot 参数）
const RouterViewStub = {
  name: 'RouterViewStub',
  setup(_, { slots }) {
    const route = { path: '/', meta: {} }
    const Comp = { template: '<div class="stub-page" />' }
    return () => slots.default?.({ Component: Comp, route })
  },
}

vi.mock('@/api', () => ({
  searchHybrid: vi.fn().mockResolvedValue({ results: [] }),
}))

import App from '@/App.vue'

function key(init) {
  window.dispatchEvent(new KeyboardEvent('keydown', init))
}

const mountApp = () => mount(App, {
  global: {
    components: { RouterView: RouterViewStub },
    stubs: {
      'el-icon': { template: '<i><slot /></i>' },
      GlowCursor: { template: '<div />' },
    },
  },
  attachTo: document.body,   // Teleport 面板挂到 body
})

describe('App 全局命令面板（⌘K）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  it('初始关闭，Ctrl+K 打开，Esc 关闭', async () => {
    const wrapper = mountApp()
    await wrapper.vm.$nextTick()
    expect(document.querySelector('.cmdk-overlay')).toBeNull()

    key({ key: 'k', ctrlKey: true, code: 'KeyK' })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('.cmdk-overlay')).not.toBeNull()

    key({ key: 'Escape', code: 'Escape' })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('.cmdk-overlay')).toBeNull()
    wrapper.unmount()
  })

  it('Meta+K 再次触发关闭已打开面板', async () => {
    const wrapper = mountApp()
    await wrapper.vm.$nextTick()
    key({ key: 'k', metaKey: true, code: 'KeyK' })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('.cmdk-overlay')).not.toBeNull()
    key({ key: 'k', metaKey: true, code: 'KeyK' })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('.cmdk-overlay')).toBeNull()
    wrapper.unmount()
  })
})
