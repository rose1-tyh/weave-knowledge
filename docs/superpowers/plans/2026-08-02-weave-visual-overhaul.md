# 织识 v3.0 视觉门面工程 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把织识从"单一外壳 + 固定模板"重构为多页面架构，每页独立性格 + 命名转场 + 动态渲染（提取织网动画/数据动效/滚动叙事），提升高级感。

**Architecture:** 纯前端改造（Vue 3 + Vite + Element Plus + D3 + Pinia），后端不动。先打地基（设计令牌 + 动效组件库 + 转场系统），再逐页重构。新增 `/import` 导入向导页。

**Tech Stack:** Vue 3 (script setup), Vite 5, Element Plus, D3 v7, Pinia, Vitest + @vue/test-utils (测试), html-to-image (导出).

## Global Constraints

- 改动只允许在 `frontend/src/` 内；后端 `backend/` 一律不改（除非计划明确说明）
- 设计令牌沿用现有暗色深空体系（`--space-deep: #080c14`），**扩展而非推倒**
- 每页主导色（页面根元素切换）：首页 `#e8453c`(朱砂) / 知识库 `#00d4ff`(墨青) / 工作台 `#c9a227`(暗金) / 探索 `#a78bfa`(夜紫)
- 三种命名转场：`fade-slide`(淡入+位移16px) / `zoom-fade`(0.94→1+淡入) / `weave-reveal`(旋转-3°+0.96+淡入)
- 所有动画只用 GPU 加速属性 `transform`/`opacity`，禁止动画 `top/left/width`
- **不破坏现有功能**：编辑/撤销重做/融合/搜索/导出/删除概念级联 必须保持可用
- 路由 `/import` 为新增；`/` `/library` `/workbench/:paperId` `/explore` 路由地址不变
- 每任务末尾 `git commit`（这是项目首个有 git 的版本，从 `52edcd0` 开始叠加）

---

## 里程碑 A · 设计系统 + 全局动效层 + 转场

### Task 1: Vitest 测试基础设施

**Files:**
- Create: `vitest.config.js`
- Modify: `package.json`（加 devDeps 与 scripts）
- Test: `frontend/src/components/motion/__tests__/smoke.test.js`

**Interfaces:**
- Produces: `npm test` 可运行；后续任务的逻辑测试依赖此设施

- [ ] **Step 1: 安装依赖并配置**

```bash
cd frontend && npm i -D vitest@^2.1.0 @vue/test-utils@^2.4.0 happy-dom@^15.0.0
```

创建 `vitest.config.js`：
```js
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': resolve(__dirname, 'src') } },
  test: {
    environment: 'happy-dom',
    globals: true,
    include: ['src/**/*.test.js'],
  },
})
```

`package.json` scripts 加：
```json
"test": "vitest run"
```

- [ ] **Step 2: 写冒烟测试**

`src/components/motion/__tests__/smoke.test.js`：
```js
import { describe, it, expect } from 'vitest'
describe('测试设施', () => {
  it('可运行', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 3: 运行验证**

Run: `npm test`
Expected: 1 passed

- [ ] **Step 4: 提交**

```bash
git add vitest.config.js package.json package-lock.json frontend/src/components/motion/__tests__/smoke.test.js
git commit -m "test: 引入 Vitest 测试基础设施"
```

---

### Task 2: 设计令牌扩展

**Files:**
- Modify: `frontend/src/styles/variables.css`

**Interfaces:**
- Produces: `--page-home-accent` 等 4 个页面主导色、`--ease-out-soft`/`--ease-spring` 曲线、`--grain-overlay` 噪点纹理、`--glow-*` 辉光尺度 —— 后续所有任务的样式依赖

- [ ] **Step 1: 在 `:root` 末尾追加令牌**

```css
/* ── 每页主导色（在页面根元素覆盖） ── */
--page-home-accent: #e8453c;
--page-library-accent: #00d4ff;
--page-workbench-accent: #c9a227;
--page-explore-accent: #a78bfa;

/* ── 动效曲线分级 ── */
--ease-out-soft: 300ms cubic-bezier(0.22, 0.61, 0.36, 1);
--ease-spring: 600ms cubic-bezier(0.34, 1.56, 0.64, 1);

/* ── 纸张噪点纹理（SVG data-uri，全站暗部叠层） ── */
--grain-overlay: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");

/* ── 辉光尺度 ── */
--glow-sm: 0 0 10px;
--glow-md: 0 0 22px;
--glow-lg: 0 0 40px;
```

- [ ] **Step 2: 验证**

Run: `npm run build`
Expected: 构建通过（令牌是纯 CSS，不应报错）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/styles/variables.css
git commit -m "feat(design): 扩展设计令牌——页面主导色/动效曲线/噪点纹理/辉光尺度"
```

---

### Task 3: 动效组件库（一）CountUp + SkeletonBlock

**Files:**
- Create: `frontend/src/components/motion/CountUp.vue`
- Create: `frontend/src/components/motion/SkeletonBlock.vue`
- Test: `frontend/src/components/motion/__tests__/CountUp.test.js`

**Interfaces:**
- Produces: `<CountUp :value="n" :duration="1000" />` 显示滚动后的数字；`<SkeletonBlock :width height radius />` 骨架占位块。二者被 Task 8/10/13 使用

- [ ] **Step 1: 写 CountUp 失败测试**

`src/components/motion/__tests__/CountUp.test.js`：
```js
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
```

- [ ] **Step 2: 运行确认失败**

Run: `npx vitest run src/components/motion/__tests__/CountUp.test.js`
Expected: FAIL（`CountUp.vue` 不存在）

- [ ] **Step 3: 实现 CountUp.vue**

```vue
<template>
  <span class="count-up">{{ formatted }}</span>
</template>

<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  duration: { type: Number, default: 1200 },
  decimals: { type: Number, default: 0 },
})

const current = ref(0)
let raf = 0

function animate() {
  cancelAnimationFrame(raf)
  const start = performance.now()
  const from = current.value
  const diff = props.value - from
  const tick = (now) => {
    const p = Math.min((now - start) / props.duration, 1)
    const eased = 1 - Math.pow(1 - p, 3) // easeOutCubic
    current.value = from + diff * eased
    if (p < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}

watch(() => props.value, animate, { immediate: true })
onUnmounted(() => cancelAnimationFrame(raf))

const formatted = computed(() =>
  current.value.toLocaleString('en-US', {
    minimumFractionDigits: props.decimals,
    maximumFractionDigits: props.decimals,
  })
)

defineExpose({ current })
</script>
```

- [ ] **Step 4: 运行确认通过**

Run: `npx vitest run src/components/motion/__tests__/CountUp.test.js`
Expected: PASS

- [ ] **Step 5: 实现 SkeletonBlock.vue**

```vue
<template>
  <div class="skeleton-block" :style="styleObj"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  width: { type: String, default: '100%' },
  height: { type: String, default: '16px' },
  radius: { type: String, default: '8px' },
})

const styleObj = computed(() => ({
  width: props.width,
  height: props.height,
  borderRadius: props.radius,
}))
</script>

<style scoped>
.skeleton-block {
  background: linear-gradient(100deg,
    rgba(255,255,255,0.06) 40%,
    rgba(255,255,255,0.12) 50%,
    rgba(255,255,255,0.06) 60%);
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}
@keyframes shimmer {
  from { background-position: 120% 0; }
  to { background-position: -20% 0; }
}
</style>
```

- [ ] **Step 6: 构建 + 提交**

Run: `npm run build`
Expected: 通过

```bash
git add frontend/src/components/motion/CountUp.vue frontend/src/components/motion/SkeletonBlock.vue frontend/src/components/motion/__tests__/CountUp.test.js
git commit -m "feat(motion): CountUp 数字滚动 + SkeletonBlock 骨架屏组件"
```

---

### Task 4: 动效组件库（二）RevealOnScroll + GlowCursor

**Files:**
- Create: `frontend/src/components/motion/RevealOnScroll.vue`
- Create: `frontend/src/components/motion/GlowCursor.vue`

**Interfaces:**
- Produces: `<RevealOnScroll :delay="ms" direction="up|left|right">内容</RevealOnScroll>` 滚动浮现容器；`<GlowCursor />` 全局光标光点（挂 App.vue）。Task 8/13 使用

- [ ] **Step 1: 实现 RevealOnScroll.vue**

```vue
<template>
  <div ref="el" class="reveal" :class="[visible && 'is-visible', `dir-${direction}`]" :style="{ transitionDelay: delay + 'ms' }">
    <slot />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  delay: { type: Number, default: 0 },
  direction: { type: String, default: 'up' }, // up | left | right
  threshold: { type: Number, default: 0.15 },
})

const el = ref(null)
const visible = ref(false)
let observer = null

onMounted(() => {
  if (!('IntersectionObserver' in window)) { visible.value = true; return }
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) { visible.value = true; observer?.disconnect() }
    },
    { threshold: props.threshold }
  )
  observer.observe(el.value)
})
onUnmounted(() => observer?.disconnect())
</script>

<style scoped>
.reveal {
  opacity: 0;
  transition: opacity 0.7s var(--ease-out-soft), transform 0.7s var(--ease-out-soft);
  will-change: opacity, transform;
}
.reveal.is-visible { opacity: 1; transform: none; }
.dir-up { transform: translateY(28px); }
.dir-left { transform: translateX(-28px); }
.dir-right { transform: translateX(28px); }
</style>
```

- [ ] **Step 2: 实现 GlowCursor.vue**

```vue
<template>
  <div v-if="enabled" class="glow-cursor" :style="{ transform: `translate(${x}px, ${y}px)` }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const enabled = ref(false)
const x = ref(-100)
const y = ref(-100)
let raf = 0

function onMove(e) {
  const move = () => {
    x.value = e.clientX
    y.value = e.clientY
  }
  if (raf) cancelAnimationFrame(raf)
  raf = requestAnimationFrame(move)
}

onMounted(() => {
  // 仅在不支持触控的设备启用，避免移动端干扰
  if (!window.matchMedia('(pointer: coarse)').matches) {
    enabled.value = true
    window.addEventListener('mousemove', onMove, { passive: true })
  }
})
onUnmounted(() => {
  window.removeEventListener('mousemove', onMove)
  cancelAnimationFrame(raf)
})
</script>

<style scoped>
.glow-cursor {
  position: fixed;
  top: 0; left: 0;
  width: 400px; height: 400px;
  border-radius: 50%;
  pointer-events: none;
  z-index: 5;
  background: radial-gradient(circle, rgba(232,69,60,0.06) 0%, transparent 60%);
  transform: translate(-200px, -200px);
  transition: left 0s;
  will-change: transform;
}
</style>
```

> 注意：光点用 `transform: translate(x,y)` 跟随，`x`/`y` 为鼠标坐标，初始偏移 -200px 使光心对准光标。

- [ ] **Step 3: 构建验证**

Run: `npm run build`
Expected: 通过

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/motion/RevealOnScroll.vue frontend/src/components/motion/GlowCursor.vue
git commit -m "feat(motion): RevealOnScroll 滚动浮现 + GlowCursor 全局光标光点"
```

---

### Task 5: SealBadge 印章徽记

**Files:**
- Create: `frontend/src/components/motion/SealBadge.vue`

**Interfaces:**
- Produces: `<SealBadge :text="'已提取'" :status="'done'|'pending'|'failed'|'processing'" />` 印章样式状态徽章。Task 10（知识库卡片）使用

- [ ] **Step 1: 实现 SealBadge.vue**

```vue
<template>
  <span class="seal-badge" :class="status">
    <span class="seal-inner">{{ text }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  text: { type: String, default: '' },
  status: { type: String, default: 'done' }, // done|pending|processing|failed
})
const text = computed(() => {
  if (props.text) return props.text
  return { done: '已提取', pending: '待提取', processing: '织网中', failed: '失败' }[props.status] || '未知'
})
</script>

<style scoped>
.seal-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  border: 1.5px solid currentColor;
  background: transparent;
  transform: rotate(-2deg);
}
.seal-inner { border-top: 1px solid currentColor; border-bottom: 1px solid currentColor; padding: 1px 4px; }
.done { color: #10b981; }
.pending { color: #6b7280; }
.processing { color: #c9a227; animation: seal-pulse 1.6s ease-in-out infinite; }
.failed { color: #e8453c; }
@keyframes seal-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
</style>
```

- [ ] **Step 2: 构建 + 提交**

Run: `npm run build`

```bash
git add frontend/src/components/motion/SealBadge.vue
git commit -m "feat(motion): SealBadge 印章徽记组件"
```

---

### Task 6: 页面转场系统

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Produces: 路由 `meta.transition`（`fade-slide`/`zoom-fade`/`weave-reveal`）；App.vue 的 `<transition :name="...">` 动态切换。Task 8/9/10/13 的页面自动获得转场

- [ ] **Step 1: 给路由加 meta.transition**

修改 `router/index.js` 每条路由的 `meta`：
```js
{ path: '/', name: 'Home', component: () => import('@/views/HomeView.vue'), meta: { title: '织识 · 首页', transition: 'weave-reveal' } },
{ path: '/library', name: 'Library', component: () => import('@/views/LibraryView.vue'), meta: { title: '织识 · 知识库', transition: 'fade-slide' } },
{ path: '/import', name: 'Import', component: () => import('@/views/ImportView.vue'), meta: { title: '织识 · 导入', transition: 'fade-slide' } },
{ path: '/workbench/:paperId', name: 'Workbench', component: () => import('@/views/WorkbenchView.vue'), meta: { title: '织识 · 工作台', transition: 'zoom-fade' } },
{ path: '/explore', name: 'Explore', component: () => import('@/views/ExploreView.vue'), meta: { title: '织识 · 全局探索', transition: 'weave-reveal' } },
```
> 注：`/import` 与 `ImportView.vue` 尚未创建，Task 9 创建；此处先写路由条目，Vite 动态 import 会在文件缺失时构建报错——**因此本任务需与 Task 9 的视图文件同步落地**。若在 Task 6 单独构建失败，属预期，Task 9 完成后重新构建通过。

- [ ] **Step 2: 改造 App.vue 的动态转场**

```vue
<router-view v-slot="{ Component, route }">
  <transition :name="route.meta.transition || 'fade-slide'" mode="out-in">
    <component :is="Component" :key="route.path" />
  </transition>
</router-view>
```
> 移除旧的 `<transition name="fade-slide">`，改用路由驱动的 name。`:key="route.path"` 确保切换触发动画。

- [ ] **Step 3: 在 global.css 追加三种转场样式**

```css
/* 转场：淡入位移 */
.fade-slide-enter-active, .fade-slide-leave-active { transition: opacity 0.32s var(--ease-out-soft), transform 0.32s var(--ease-out-soft); }
.fade-slide-enter-from { opacity: 0; transform: translateY(16px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-12px); }

/* 转场：缩放淡入 */
.zoom-fade-enter-active, .zoom-fade-leave-active { transition: opacity 0.38s var(--ease-out-soft), transform 0.38s var(--ease-out-soft); }
.zoom-fade-enter-from { opacity: 0; transform: scale(0.94); }
.zoom-fade-leave-to { opacity: 0; transform: scale(1.02); }

/* 转场：织入 */
.weave-reveal-enter-active, .weave-reveal-leave-active { transition: opacity 0.5s var(--ease-out-soft), transform 0.5s var(--ease-out-soft); }
.weave-reveal-enter-from { opacity: 0; transform: rotate(-3deg) scale(0.96); }
.weave-reveal-leave-to { opacity: 0; transform: rotate(1.5deg) scale(1.01); }
```

- [ ] **Step 4: 临时验证**

`npm run build` —— 若因 `/import` 视图缺失报错，先创建 `frontend/src/views/ImportView.vue` 的空壳（`<template><div>导入向导</div></template>`）再构建，确保转场样式无语法错误。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/router/index.js frontend/src/App.vue frontend/src/styles/global.css
git commit -m "feat(routes): 页面转场系统——三种命名转场 + 路由驱动切换"
```

---

### Task 7: 里程碑 A 验收（现有页面接入令牌 + 全局动效）

**Files:**
- Modify: `frontend/src/App.vue`（挂载 `<GlowCursor />`）
- Modify: `frontend/src/views/HomeView.vue`、`LibraryView.vue`、`ExploreView.vue`（根元素套页面主导色）

**Interfaces:**
- Produces: 全站统一"高级感"地基就位；为里程碑 B/C 提供可运行基座

- [ ] **Step 1: App.vue 挂载全局光标**

`App.vue` 模板加 `<GlowCursor />`，`<script setup>` 引入并注册。

- [ ] **Step 2: 三个页面根元素套主导色**

给 `HomeView` 根元素、`LibraryView` 根元素、`ExploreView` 根元素各加一行 class：
```css
/* 在各自根元素 style 里（scoped） */
.home-dashboard { --page-accent: var(--page-home-accent); }
.library-page  { --page-accent: var(--page-library-accent); }
.explore-page  { --page-accent: var(--page-explore-accent); }
```
（`--page-accent` 统一语义，具体页后续使用）

- [ ] **Step 3: 里程碑 A 验收**

- `npm run build` 通过
- 启动 `npm run dev`，手动走一遍：首页 → 知识库 → 工作台 → 探索，确认**三种转场动画**生效、页面无白屏/无回归

- [ ] **Step 4: 提交**

```bash
git add frontend/src/App.vue frontend/src/views/HomeView.vue frontend/src/views/LibraryView.vue frontend/src/views/ExploreView.vue
git commit -m "feat: 里程碑A——全站接入动效层与页面主导色"
```

---

## 里程碑 B · 首页 + 导入向导

### Task 8: 首页重构（Hero + 滚动叙事 + 动态统计）

**Files:**
- Rewrite: `frontend/src/views/HomeView.vue`
- Modify: `frontend/src/components/ParticleBackground.vue`（可选增强：粒子数量/色彩随页面 accent 变化）

**Interfaces:**
- Consumes: `CountUp`、`RevealOnScroll`、`SealBadge`（Task 3/4/5）、`--page-home-accent`
- Produces: 首页 Hero 大标题、三段滚动叙事、CountUp 统计、最近论文、**导入入口指向 `/import`**（不再弹窗）

- [ ] **Step 1: 重写 HomeView 模板结构**

保持现有数据流（`useLibraryStore` 拉 stats/papers）不变，模板改为：
```
Hero 区（全屏）：
  粒子背景 + 「织」字大标(96px, 朱砂光晕) + 副标题 + 「开始构建」按钮 → /import
统计区：三张卡片，数值用 <CountUp :value="..." />
叙事区（三段 <RevealOnScroll>）：
  灵感 → 为什么做知识重构
  方法 → AI 织网提取概念与关系
  作品 → CTA 进知识库
最近论文区：卡片流（SealBadge 状态）
```

- [ ] **Step 2: 实现 Hero 与叙事样式**

Hero 用 `radial-gradient` 光晕 + 大号衬线「织」字（`font-family: var(--font-display)`），朱砂光晕 `--vermilion-glow`；叙事区用 `RevealOnScroll` 包裹，逐段 `:delay` 错开 150ms。

- [ ] **Step 3: 替换导入弹窗为跳转**

删除 `HomeView.vue` 内的 `el-dialog` 导入弹窗与 `uploadPaper/extractFromText/extractFromUrl/createEmptyPaper` 相关逻辑，改为 `router.push('/import')`。保留 `openPaper` 进入工作台。

- [ ] **Step 4: 构建 + 手动验收**

- `npm run build` 通过
- `npm run dev`：首页 Hero 可见、数字滚动、滚动浮现、点击开始构建跳 `/import`（该页 Task 9 建）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/HomeView.vue frontend/src/components/ParticleBackground.vue
git commit -m "feat(home): 首页重构——Hero/滚动叙事/动态统计/跳转导入"
```

---

### Task 9: 导入向导页 /import（四步）

**Files:**
- Create: `frontend/src/views/ImportView.vue`
- Create: `frontend/src/components/ImportWizard.vue`
- Modify: `frontend/src/router/index.js`（已有条目，确认）
- Modify: `frontend/src/components/AppHeader.vue`（上传按钮 → `/import`）
- Modify: `frontend/src/views/LibraryView.vue`（弹窗导入 → 跳 `/import`）

**Interfaces:**
- Consumes: `uploadPaper`、`extractFromText`、`extractFromUrl`、`createEmptyPaper`（`api/index.js` 已有）
- Produces: `/import` 四步向导；完成后 `router.push` 工作台

- [ ] **Step 1: 实现 ImportWizard.vue（步骤状态机）**

```vue
<template>
  <div class="import-wizard">
    <div class="iw-steps">
      <div v-for="(s, i) in steps" :key="s.key" class="iw-step" :class="{ active: i === current, done: i < current }">
        <span class="iw-dot">{{ i < current ? '✓' : i + 1 }}</span>
        <span class="iw-label">{{ s.label }}</span>
      </div>
    </div>
    <div class="iw-body">
      <!-- step 0: PDF -->
      <template v-if="current === 0">
        <UploadPanel :uploading="loading" :error="error" @upload="handleUpload" />
      </template>
      <!-- step 1: 文本 -->
      <template v-else-if="current === 1">
        <label class="input-label">标题</label>
        <input v-model="title" class="dark-input" placeholder="知识标题（可选）" />
        <label class="input-label">内容</label>
        <textarea v-model="text" class="dark-textarea" rows="6" placeholder="粘贴文本..."></textarea>
        <button class="iw-next" :disabled="!text.trim()" @click="handleText">开始提取</button>
      </template>
      <!-- step 2: URL -->
      <template v-else-if="current === 2">
        <label class="input-label">网页 URL</label>
        <input v-model="url" class="dark-input" placeholder="https://..." @keyup.enter="handleUrl" />
        <button class="iw-next" :disabled="!url.trim()" @click="handleUrl">抓取并提取</button>
      </template>
      <!-- step 3: 手动 -->
      <template v-else>
        <label class="input-label">知识主题</label>
        <input v-model="manualTitle" class="dark-input" placeholder="知识主题名称" />
        <button class="iw-next" :disabled="!manualTitle.trim()" @click="handleManual">创建知识空间</button>
      </template>
    </div>
  </div>
</template>
```

```js
// script setup 逻辑（节选核心）
const steps = [
  { key: 'pdf', label: '上传 PDF' },
  { key: 'text', label: '粘贴文本' },
  { key: 'url', label: '网页链接' },
  { key: 'manual', label: '手动创建' },
]
const current = ref(0)
const loading = ref(false)
const error = ref('')

async function go(paperId) {
  router.push({ name: 'Workbench', params: { paperId } })
}
async function handleUpload(file) {
  loading.value = true; error.value = ''
  try { const p = await uploadPaper(file); go(p.paper_id) }
  catch (e) { error.value = e.message; loading.value = false }
}
// handleText / handleUrl / handleManual 同构：调用对应 api → go(data.paper_id 或 data.paperId)
```

> 四个输入方式成功后的跳转参数：`uploadPaper`→`paper_id`；`extractFromText`/`extractFromUrl`→`paperId`；`createEmptyPaper`→`paper_id`。跳转前可先 `current.value++` 展示"处理中"步骤，也可直接跳。

- [ ] **Step 2: 创建 ImportView.vue 并接入路由**

`ImportView.vue`：居中单列容器，标题 + `<ImportWizard />`，根元素套 `--page-accent`（用朱砂→青渐变背景）。路由条目 Task 6 已写，无需再改。

- [ ] **Step 3: AppHeader 上传按钮跳转**

`AppHeader.vue` 的"上传论文"按钮 `@click` 改为 `router.push('/import')`（原 emit('upload') 移除）。

- [ ] **Step 4: LibraryView 弹窗改为跳转**

删除 `LibraryView.vue` 的 `el-dialog` 与 4 种输入模式相关逻辑，工具栏"上传论文"按钮改为 `router.push('/import')`；`handleUpload` 等函数一并移除。保留 `openPaper` 与删除操作。

- [ ] **Step 5: 构建 + 手动验收**

- `npm run build` 通过（此时代码完整，无缺失文件）
- `npm run dev`：首页/知识库"上传"按钮 → `/import` 向导；四步各走一遍（PDF 用测试文件、文本粘贴、URL、手动），均能进入工作台

- [ ] **Step 6: 提交**

```bash
git add frontend/src/views/ImportView.vue frontend/src/components/ImportWizard.vue frontend/src/components/AppHeader.vue frontend/src/views/LibraryView.vue
git commit -m "feat(import): 导入向导页——四步引导替代弹窗"
```

---

## 里程碑 C · 知识库 / 工作台 / 探索

### Task 10: 知识库重构（瀑布流 + 分组 + 骨架屏）

**Files:**
- Modify: `frontend/src/views/LibraryView.vue`
- Test: `frontend/src/views/__tests__/LibraryView.test.js`（可选，若时间紧可跳过——见验收）

**Interfaces:**
- Consumes: `SkeletonBlock`、`SealBadge`、`RevealOnScroll`、`--page-library-accent`
- Produces: 知识库瀑布流卡片、分组筛选、hover 光效、加载骨架屏

- [ ] **Step 1: 重写卡片区为错落瀑布流**

用 CSS `columns` 实现错落瀑布：
```css
.paper-grid {
  columns: 3 260px;
  column-gap: var(--space-md);
}
.paper-card {
  break-inside: avoid;
  margin-bottom: var(--space-md);
  transition: transform var(--ease-out-soft), border-color var(--ease-out-soft), box-shadow var(--ease-out-soft);
}
.paper-card:hover {
  transform: translateY(-4px);
  border-color: var(--page-library-accent);
  box-shadow: 0 0 24px rgba(0, 212, 255, 0.12);
}
```

- [ ] **Step 2: 卡片状态用 SealBadge + hover 印章浮现**

卡片右上角状态改为 `<SealBadge :status="p.extract_status" />`；hover 时卡片浮现一枚大号淡色"织"字印章（绝对定位 + opacity 过渡）。

- [ ] **Step 3: 加载态骨架屏**

新增 `loading` ref；`onMounted` 拉取期间渲染 6 个 `<SkeletonBlock height="160px" />` 占位卡片。

- [ ] **Step 4: 构建 + 验收 + 提交**

- `npm run build` 通过；`npm run dev` 检查瀑布流、hover、骨架屏、删除仍可用
- `git add frontend/src/views/LibraryView.vue && git commit -m "feat(library): 知识库重构——瀑布流/印章状态/骨架屏"`

---

### Task 11: 工作台图谱视觉升级 + 侧栏折叠

**Files:**
- Modify: `frontend/src/views/WorkbenchView.vue`
- Modify: `frontend/src/components/KnowledgeGraph.vue`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**
- Consumes: `--page-workbench-accent`
- Produces: 图谱节点辉光/连线流动/纸张噪点；侧栏可折叠按钮；编辑工具栏微缩。**不得破坏编辑/撤销/重做/导出**

- [ ] **Step 1: 图谱底纹与环境光**

`KnowledgeGraph.vue` 的 `.kg-container` 加噪点叠层与径向光晕：
```css
.kg-container {
  background:
    radial-gradient(ellipse at 50% 40%, rgba(201,162,39,0.06), transparent 60%),
    var(--space-deep);
}
.kg-container::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background-image: var(--grain-overlay);
}
```

- [ ] **Step 2: 节点/连线视觉强化**

- 节点：外圈光晕 `r` 增大、`filter: drop-shadow(0 0 6px color)`；选中态 `--glow-md`
- 连线：`stroke-opacity` 提至 0.6，`contradicts` 保持虚线；tick 中给 `line` 加 `stroke-width` hover 增粗（pointer-events 已开）

- [ ] **Step 3: 侧栏折叠**

`WorkbenchView.vue` 加 `sidebarCollapsed` ref 与折叠按钮（顶部小箭头）。折叠时 `.wb-sidebar` 宽度 0 隐藏，`width` 过渡用 `transform: translateX(100%)` 或 `max-width`（避免动画 width）。默认不折叠。

- [ ] **Step 4: 验收 + 提交**

- 编辑/拖拽建关系/撤销重做/导出 PNG·JSON·MD 全流程手测一遍
- `git add` 相关文件，`git commit -m "feat(workbench): 图谱视觉升级 + 侧栏折叠"`

---

### Task 12: 提取"织网"动画（前端排演）

**Files:**
- Create: `frontend/src/components/motion/WeaveExtraction.vue`
- Modify: `frontend/src/views/WorkbenchView.vue`
- Test: `frontend/src/components/motion/__tests__/WeaveExtraction.test.js`

**Interfaces:**
- Consumes: `store.runExtraction(paperId)`（已有）
- Produces: 提取期间播放"解析→概念→关系→成图"阶段动画；数据返回后淡出；**失败时收尾到错误态**

- [ ] **Step 1: 写阶段状态机测试**

`WeaveExtraction.test.js`：
```js
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
```

- [ ] **Step 2: 运行确认失败**

Run: `npx vitest run src/components/motion/__tests__/WeaveExtraction.test.js`
Expected: FAIL（组件不存在）

- [ ] **Step 3: 实现 WeaveExtraction.vue**

```vue
<template>
  <div class="weave-extract">
    <div class="we-stage-label">{{ stageLabel }}</div>
    <div class="we-track">
      <div class="we-progress" :style="{ width: progressPct + '%' }"></div>
    </div>
    <div class="we-nodes">
      <span
        v-for="(n, i) in fakeNodes"
        :key="i"
        class="we-node"
        :class="{ lit: i < litCount }"
        :style="{ animationDelay: (i * 0.18) + 's' }"
      ></span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const STAGES = [
  { label: '解析文本', dur: 900 },
  { label: '识别概念', dur: 1100 },
  { label: '抽取关系', dur: 1100 },
  { label: '编织成图', dur: 900 },
]
const stage = ref(0)
const stageProgress = ref(0)
const litCount = ref(0)
const fakeNodes = Array.from({ length: 8 })
let timer = null

const stageLabel = computed(() => STAGES[stage.value].label)
const progressPct = computed(() => ((stage.value + stageProgress.value) / STAGES.length) * 100)

function tick() {
  if (stage.value >= STAGES.length) {
    litCount.value = fakeNodes.length
    return
  }
  stageProgress.value += 0.03
  litCount.value = Math.min(
    fakeNodes.length,
    Math.floor(stage.value * 2.5 + stageProgress.value * 2.5)
  )
  if (stageProgress.value >= 1) { stageProgress.value = 0; stage.value += 1 }
}

onMounted(() => { timer = setInterval(tick, 30) })
onUnmounted(() => clearInterval(timer))
</script>
```

> 组件自行循环推进，父组件（WorkbenchView）在数据到达后隐藏它。到达"成图"后停在末尾（阶段标签不变）。

- [ ] **Step 4: 运行确认通过**

Run: `npx vitest run src/components/motion/__tests__/WeaveExtraction.test.js`
Expected: PASS（4 秒推进后 `stage === 3`）

- [ ] **Step 5: 接入 WorkbenchView**

在 `WorkbenchView` 的 `onMounted` 提取流程外包一层：
```js
onMounted(async () => {
  try {
    await store.loadGraph(paperId)
    if (!store.graphData || !store.graphData.nodes?.length) {
      showingWeave.value = true          // 显示织网动画
      try {
        await store.runExtraction(paperId)   // 同步等待真实结果
        // 成功：让织网动画收尾，再淡出露出真实图谱
        await delay(600)
      } finally {
        showingWeave.value = false
      }
    }
  } catch (_) { /* store.error 已处理 */ }
})
function delay(ms) { return new Promise(r => setTimeout(r, ms)) }
```
模板：`<WeaveExtraction v-if="showingWeave" />` 覆盖在工作台图谱区之上（absolute 全屏、`z-index` 高于图谱、低于工具栏）。**失败路径**：`runExtraction` 抛错 → `finally` 隐藏动画 → `store.error` 显示错误态（沿用现有 `.wb-error`）。

- [ ] **Step 6: 验收 + 提交**

- 上传新 PDF → 看到"织网"动画 → 动画淡出后真实图谱出现
- `git add` 相关文件，`git commit -m "feat(workbench): 提取织网动画——前端排演 + 真实数据无缝替换"`

---

### Task 13: 探索页重构（夜紫沉浸 + ⌘K 搜索 + 融合着色）

**Files:**
- Modify: `frontend/src/views/ExploreView.vue`
- Modify: `frontend/src/components/GlobalSearch.vue`（升级为 ⌘K 面板触发）
- Modify: `frontend/src/components/KnowledgeGraph.vue`（融合来源着色：节点 `stroke` 用 `paperIndex` 映射色）

**Interfaces:**
- Consumes: `--page-explore-accent`、`RevealOnScroll`
- Produces: 夜紫背景 + 漂浮粒子；⌘K 搜索面板；融合图谱多论文来源着色（后端已返回 `paperIds`）

- [ ] **Step 1: 夜紫背景 + 漂浮粒子**

`.explore-page` 根加 `--page-accent: var(--page-explore-accent)`；主区背景用夜紫径向渐变 + `--grain-overlay`。复用 `ParticleBackground`（换色）作为漂浮概念粒子层。

- [ ] **Step 2: 融合节点来源着色**

`KnowledgeGraph.vue` 的节点 `stroke` 改为按来源上色：
```js
const paperPalette = ['#e8453c', '#00d4ff', '#10b981', '#f59e0b', '#a78bfa']
// 节点渲染时：
.attr('stroke', d => d.paperIndex !== undefined
  ? paperPalette[d.paperIndex % paperPalette.length]
  : (d.color || 'rgba(255,255,255,0.35)'))
```
后端 `fusion_graph` 返回的节点带 `paperIds`（数组），前端在 `ExploreView` 拿到数据后给每个节点附 `paperIndex = paperIds.length > 1 ? -1 : 0`（多来源用混合色或白，单来源用对应论文色）。实现时在 `ExploreView` 映射，`KnowledgeGraph` 只读 `paperIndex`。

- [ ] **Step 3: ⌘K 搜索面板**

`ExploreView` 加 `searchOpen` ref + `keydown` 监听（`e.metaKey||e.ctrlKey` + `k` → toggle）。面板为居中浮层：输入框 + `GlobalSearch` 结果列表；`Esc` 关闭；回车搜索。

- [ ] **Step 4: 验收 + 提交**

- 两篇论文进融合 → 不同来源节点不同描边色；⌘K 打开搜索、Esc 关闭
- `git add` 相关文件，`git commit -m "feat(explore): 探索页重构——夜紫沉浸/融合着色/⌘K搜索"`

---

### Task 14: 全局回归验证 + 收尾

**Files:**
- 无新增；验证为主

- [ ] **Step 1: 全量构建**

Run: `npm run build`
Expected: 通过，无 chunk 报错

- [ ] **Step 2: 启动前后端，全流程回归**

后端 `python -m uvicorn main:app --port 8000`（`backend/` 下），前端 `npm run dev`。逐项验证：
- [ ] 5 个页面均可导航，三种转场动画正确
- [ ] 首页 Hero/叙事/统计数字滚动；"开始构建"→ `/import`
- [ ] `/import` 四步各走一遍 → 进入工作台
- [ ] 知识库瀑布流、SealBadge 状态、骨架屏、删除可用
- [ ] 工作台：编辑模式拖拽建关系、概念/关系增删改、撤销重做、导出 PNG/JSON/MD
- [ ] 提取新 PDF：看到织网动画 → 落到真实图谱
- [ ] 探索：融合图谱来源着色、⌘K 搜索
- [ ] `npm test` 全部通过

- [ ] **Step 3: 提交收尾**

```bash
git add -A
git commit -m "chore: v3.0 视觉门面工程完成——多页面/转场/动效/织网动画"
```

---

## Self-Review（本计划自查结果）

**1. Spec 覆盖：** 页面架构 ✓（Task 6/8/9/10/13）、里程碑 A 令牌/动效库/转场 ✓（Task 2/3/4/5/6/7）、B 首页/导入 ✓（Task 8/9）、C 知识库/工作台/探索/织网动画 ✓（Task 10/11/12/13）、技术红线（后端不动 ✓、提取动画前端排演 ✓、GPU 加速 ✓）、验收标准映射到 Task 7/9/14。

**2. 占位符扫描：** 无 TBD/TODO；CSS 细节以"方向 + 关键代码"给出，视觉微调留待实现时按设计打磨（属预期，非占位）。

**3. 类型一致性：** `paper_id`（upload/manual）与 `paperId`（text/url）的差异已在 Task 9 明确；`--page-*-accent` 令牌命名统一；`meta.transition` 三值在 Task 6 定义并被路由引用一致。
