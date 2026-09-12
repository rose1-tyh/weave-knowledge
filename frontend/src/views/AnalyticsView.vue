<template>
  <div class="analytics-page">
    <ParticleBackground :accent="'#f59e0b'" :density="40" :opacity="0.3" />

    <!-- 页头：标题 + 范围切换 -->
    <header class="ana-head">
      <div>
        <h2 class="ana-title">知识洞察</h2>
        <p class="ana-sub">概念构成 · PageRank 核心概念 · 跨论文重合</p>
      </div>
      <el-select v-model="scope" class="ana-scope" size="default" data-test="scope-select">
        <el-option label="全库视图" value="" />
        <el-option v-for="p in papers" :key="p.id" :label="p.title" :value="p.id" />
      </el-select>
    </header>

    <div v-if="loading" class="ana-loading">
      <div class="loading-dots"><span></span><span></span><span></span></div>
      <p>正在统计…</p>
    </div>

    <div v-else-if="empty" class="ana-empty">
      <p class="ana-empty-seal">空</p>
      <p>还没有可分析的知识 —— 先去导入一篇论文吧</p>
      <el-button type="primary" size="small" @click="$router.push('/import')">上传论文</el-button>
    </div>

    <div v-else class="ana-grid">
      <!-- 概念类型分布（环图） -->
      <section class="ana-card glass-panel">
        <h3>概念类型分布</h3>
        <div class="donut-wrap">
          <svg :viewBox="`0 0 ${DONUT.box} ${DONUT.box}`" class="donut-svg" role="img" aria-label="概念类型分布环图">
            <path v-for="s in donutSlices" :key="s.type" :d="slicePath(s)" :fill="s.color"
              :opacity="hoverSlice && hoverSlice !== s.type ? 0.35 : 0.92"
              @mouseenter="hoverSlice = s.type" @mouseleave="hoverSlice = null" />
            <text :x="DONUT.box / 2" :y="DONUT.box / 2 - 4" text-anchor="middle" class="donut-total">
              {{ data.totals.concepts }}
            </text>
            <text :x="DONUT.box / 2" :y="DONUT.box / 2 + 14" text-anchor="middle" class="donut-cap">概念</text>
          </svg>
          <ul class="donut-legend">
            <li v-for="s in donutSlices" :key="s.type">
              <i :style="{ background: s.color }"></i>
              <span class="lg-label">{{ s.label }}</span>
              <span class="lg-val">{{ s.count }} · {{ Math.round(s.percent * 100) }}%</span>
            </li>
          </ul>
        </div>
      </section>

      <!-- 关系类型构成（条形） -->
      <section class="ana-card glass-panel">
        <h3>关系类型构成</h3>
        <ul class="bar-list" data-test="relation-bars">
          <li v-for="r in data.relationTypes" :key="r.type">
            <span class="bar-label">{{ r.label }}</span>
            <span class="bar-track">
              <span class="bar-fill rel" :style="{ width: barW(r.count, maxRelation) }"></span>
            </span>
            <span class="bar-val">{{ r.count }}</span>
          </li>
          <li v-if="!data.relationTypes.length" class="bar-none">暂无关系</li>
        </ul>
      </section>

      <!-- 核心概念 Top N（PageRank 条形） -->
      <section class="ana-card glass-panel">
        <h3>核心概念 Top {{ data.keyConcepts.length }} <span class="ana-cap">PageRank · 节点枢纽度</span></h3>
        <ul class="bar-list" data-test="key-concepts">
          <li v-for="(k, i) in data.keyConcepts" :key="k.name + i">
            <span class="bar-label kc" :title="k.name">{{ i + 1 }}. {{ k.name }}</span>
            <span class="bar-track">
              <span class="bar-fill key" :style="{ width: barW(k.pagerank, maxPagerank) }"></span>
            </span>
            <span class="bar-val">{{ (k.pagerank * 100).toFixed(1) }}</span>
          </li>
          <li v-if="!data.keyConcepts.length" class="bar-none">暂无概念</li>
        </ul>
      </section>

      <!-- 跨论文重合 / 论文贡献 -->
      <section class="ana-card glass-panel">
        <h3>{{ isGlobal ? '跨论文概念重合' : '本篇概览' }}</h3>
        <template v-if="isGlobal">
          <ul class="overlap-list" data-test="overlap-list">
            <li v-for="o in data.crossPaperOverlap" :key="o.name">
              <span class="ov-name">{{ o.name }}</span>
              <span class="ov-papers">{{ o.paperIds.length }} 篇共现</span>
            </li>
            <li v-if="!data.crossPaperOverlap.length" class="bar-none">
              暂无跨论文同名概念 —— 多导入几篇试试
            </li>
          </ul>
          <h3 v-if="papers.length" class="ana-h3-2">论文贡献</h3>
          <ul class="paper-contrib">
            <li v-for="p in data.papers || []" :key="p.id" @click="scope = p.id">
              <span class="pc-title" :title="p.title">{{ p.title }}</span>
              <span class="pc-meta">{{ p.conceptCount }} 概念 · {{ p.relationCount }} 关系</span>
            </li>
          </ul>
        </template>
        <template v-else>
          <ul class="overlap-list">
            <li v-for="o in data.crossPaperOverlap" :key="o.name">
              <span class="ov-name">{{ o.name }}</span>
              <span class="ov-papers">{{ o.paperIds.length }} 处出现</span>
            </li>
            <li v-if="!data.crossPaperOverlap.length" class="bar-none">暂无重合概念</li>
          </ul>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { analyticsOverview } from '@/api'
import { useLibraryStore } from '@/stores/library'
import { useApiError } from '@/composables/useApiError'
import { donutSlice, buildDonutSlices, barWidth } from '@/utils/charts'
import ParticleBackground from '@/components/ParticleBackground.vue'

const lib = useLibraryStore()
const { showError } = useApiError()

const scope = ref('')          // '' = 全库
const data = ref(null)
const loading = ref(false)
const papers = ref([])
const hoverSlice = ref(null)

const DONUT = { box: 200, rOuter: 88, rInner: 56 }

const isGlobal = computed(() => !scope.value)
const empty = computed(() => !loading.value && data.value && !data.value.totals.concepts)

const donutSlices = computed(() =>
  buildDonutSlices((data.value?.conceptTypes || []).map(t => ({
    type: t.type, label: t.label, value: t.count, color: t.color,
  }))))

function slicePath(s) {
  return donutSlice(DONUT.box / 2, DONUT.box / 2, DONUT.rInner, DONUT.rOuter, s.a0, s.a1)
}

const maxRelation = computed(() => Math.max(0, ...(data.value?.relationTypes || []).map(r => r.count)))
const maxPagerank = computed(() => Math.max(0, ...(data.value?.keyConcepts || []).map(k => k.pagerank)))

function barW(value, max) {
  return barWidth(value, max, 100) + '%'
}

async function load() {
  loading.value = true
  try {
    data.value = await analyticsOverview(scope.value)
  } catch (e) {
    showError(e, '统计分析加载失败')
  } finally {
    loading.value = false
  }
}

watch(scope, load)
onMounted(async () => {
  try {
    await lib.fetchPapers()
    papers.value = lib.papers
  } catch { /* 下拉为空不阻塞主视图 */ }
  await load()
})
</script>

<style scoped>
.analytics-page {
  --page-accent: #f59e0b;
  position: relative;
  height: 100%;
  overflow-y: auto;
  padding: var(--space-lg) var(--space-xl) var(--space-2xl);
  background: var(--space-deep);
}
.analytics-page::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: var(--grain-overlay);
}

.ana-head {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: var(--space-lg);
  gap: var(--space-md);
  flex-wrap: wrap;
}
.ana-title {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  color: var(--text-primary);
}
.ana-sub { font-size: var(--text-sm); color: var(--text-muted); margin-top: 4px; }
.ana-scope { width: 240px; }

.ana-loading, .ana-empty {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  min-height: 50vh;
  color: var(--text-muted);
}
.ana-empty-seal {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--vermilion);
  border-radius: var(--radius-md);
  color: var(--vermilion);
  font-family: var(--font-display);
  font-size: var(--text-xl);
  transform: rotate(-4deg);
}

.ana-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-lg);
}
@media (max-width: 960px) {
  .ana-grid { grid-template-columns: 1fr; }
}

.ana-card {
  padding: var(--space-lg);
  background: var(--space-surface);
}
.ana-card h3 {
  font-family: var(--font-display);
  font-size: var(--text-md);
  color: var(--text-primary);
  margin-bottom: var(--space-md);
}
.ana-cap {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: 400;
  color: var(--text-muted);
  margin-left: var(--space-sm);
}
.ana-h3-2 { margin-top: var(--space-lg); }

/* 环图 */
.donut-wrap { display: flex; align-items: center; gap: var(--space-lg); }
.donut-svg { width: 180px; height: 180px; flex-shrink: 0; }
.donut-svg path { cursor: pointer; transition: opacity var(--ease-out); }
.donut-total {
  fill: var(--text-primary);
  font-family: var(--font-display);
  font-size: 30px;
}
.donut-cap { fill: var(--text-muted); font-size: 11px; letter-spacing: 0.2em; }
.donut-legend { flex: 1; min-width: 0; }
.donut-legend li {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: 4px 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.donut-legend i { width: 9px; height: 9px; border-radius: 2px; flex-shrink: 0; }
.lg-label { flex: 1; }
.lg-val { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--text-muted); }

/* 条形列表 */
.bar-list { display: flex; flex-direction: column; gap: 10px; }
.bar-list li { display: flex; align-items: center; gap: var(--space-sm); }
.bar-label {
  width: 96px;
  flex-shrink: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-label.kc { width: 130px; }
.bar-track {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: var(--space-surface);
  overflow: hidden;
}
.bar-fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  transition: width 600ms var(--ease-out-soft);
}
.bar-fill.rel { background: linear-gradient(90deg, var(--cyan), var(--violet)); }
.bar-fill.key { background: linear-gradient(90deg, var(--vermilion), var(--amber)); }
.bar-val { width: 42px; text-align: right; font-family: var(--font-mono); font-size: var(--text-xs); color: var(--text-muted); }
.bar-none { color: var(--text-muted); font-size: var(--text-sm); }

/* 跨论文重合 / 论文贡献 */
.overlap-list { display: flex; flex-direction: column; }
.overlap-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 0;
  border-bottom: 1px dashed var(--border-subtle);
  font-size: var(--text-sm);
}
.ov-name { color: var(--text-primary); }
.ov-papers { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--amber); }

.paper-contrib { display: flex; flex-direction: column; }
.paper-contrib li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: 7px 8px;
  margin: 0 -8px;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--ease-out);
}
.paper-contrib li:hover { background: var(--hover-tint); }
.pc-title { color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.paper-contrib li:hover .pc-title { color: var(--text-primary); }
.pc-meta { flex-shrink: 0; font-family: var(--font-mono); font-size: var(--text-xs); color: var(--text-muted); }
</style>
