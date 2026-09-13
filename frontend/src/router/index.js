import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('@/views/HomeView.vue'), meta: { title: '织识 · 首页', transition: 'weave-reveal' } },
  { path: '/library', name: 'Library', component: () => import('@/views/LibraryView.vue'), meta: { title: '织识 · 知识库', transition: 'fade-slide' } },
  { path: '/import', name: 'Import', component: () => import('@/views/ImportView.vue'), meta: { title: '织识 · 导入', transition: 'fade-slide' } },
  { path: '/workbench/:paperId', name: 'Workbench', component: () => import('@/views/WorkbenchView.vue'), meta: { title: '织识 · 工作台', transition: 'zoom-fade' } },
  { path: '/explore', name: 'Explore', component: () => import('@/views/ExploreView.vue'), meta: { title: '织识 · 全局探索', transition: 'weave-reveal' } },
  { path: '/analytics', name: 'Analytics', component: () => import('@/views/AnalyticsView.vue'), meta: { title: '织识 · 知识洞察', transition: 'fade-slide' } },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta.title || '织识'
  // 记录最近路由：桌面应用模式下下次启动恢复（见下方 maybeRestoreLastRoute）
  try { localStorage.setItem('weave-last-route', to.fullPath) } catch { /* 忽略 */ }
})

// 桌面应用模式（后端 /api/health 的 appMode 标记，由 run.py 设置 WEAVE_APP_MODE）：
// 启动时恢复上次浏览的页面；浏览器模式保持常规行为（URL 即入口）
async function maybeRestoreLastRoute() {
  try {
    const resp = await fetch('/api/health')
    const data = await resp.json()
    if (!data.appMode) return
    const last = localStorage.getItem('weave-last-route')
    if (last && last !== '/' && last !== router.currentRoute.value.fullPath) {
      router.replace(last)
    }
  } catch { /* 非关键路径：探测失败即留在默认页 */ }
}
maybeRestoreLastRoute()

export default router
