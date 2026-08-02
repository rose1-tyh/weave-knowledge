import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('@/views/HomeView.vue'), meta: { title: '织识 · 首页', transition: 'weave-reveal' } },
  { path: '/library', name: 'Library', component: () => import('@/views/LibraryView.vue'), meta: { title: '织识 · 知识库', transition: 'fade-slide' } },
  { path: '/import', name: 'Import', component: () => import('@/views/ImportView.vue'), meta: { title: '织识 · 导入', transition: 'fade-slide' } },
  { path: '/workbench/:paperId', name: 'Workbench', component: () => import('@/views/WorkbenchView.vue'), meta: { title: '织识 · 工作台', transition: 'zoom-fade' } },
  { path: '/explore', name: 'Explore', component: () => import('@/views/ExploreView.vue'), meta: { title: '织识 · 全局探索', transition: 'weave-reveal' } },
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
})

export default router
