<template>
  <div class="home-page">
        <router-link v-if="needsKey" to="/settings" class="byok-banner" data-test="byok-banner">
      <el-icon><Key /></el-icon>
      首次使用：配置你自己的 API Key 以启用 AI 提取（支持 DeepSeek / 智谱 GLM / Kimi 等） →
    </router-link>
<ParticleBackground :accent="'#e8453c'" :density="72" :opacity="0.55" />

    <!-- ══════════ Hero ══════════ -->
    <section class="hero">
      <div class="hero-halo" aria-hidden="true"></div>
      <div class="hero-content">
        <span class="hero-eyebrow">织识 · WEAVE</span>
        <h1 class="hero-mark">
          <span class="hero-char">织</span>
        </h1>
        <p class="hero-subtitle">将文献编织为知识网络</p>
        <p class="hero-desc">上传论文，AI 提取概念与关系 —— 让散落的碎片，长成你自己的知识体系。</p>
        <div class="hero-actions">
          <button class="btn-primary" @click="goImport">
            <span class="btn-plus">+</span>开始构建
          </button>
          <router-link to="/library" class="btn-ghost">进入知识库</router-link>
        </div>
      </div>
      <div class="hero-scroll" aria-hidden="true">
        <span class="scroll-line"></span>
        <span class="scroll-text">向下探索</span>
      </div>
    </section>

    <!-- ══════════ 统计（CountUp） ══════════ -->
    <section class="stats-section">
      <div class="container">
        <RevealOnScroll :delay="0" direction="up">
          <div class="section-head stats-head">
            <span class="section-eyebrow">织识 · LIVE</span>
            <h2 class="section-heading">知识网的规模</h2>
          </div>
        </RevealOnScroll>
        <div class="stats-row">
          <RevealOnScroll v-for="(s, i) in statCards" :key="s.label" :delay="i * 150" direction="up">
            <div class="stat-card glass-panel">
              <div class="stat-icon" :class="s.accent"><el-icon :size="22"><component :is="s.icon" /></el-icon></div>
              <div class="stat-body">
                <span class="stat-value"><CountUp :value="s.value" /></span>
                <span class="stat-label">{{ s.label }}</span>
              </div>
            </div>
          </RevealOnScroll>
        </div>
      </div>
    </section>

    <!-- ══════════ 三段滚动叙事 ══════════ -->
    <section class="narrative-section">
      <div class="container">
        <RevealOnScroll :delay="0" direction="up">
          <div class="section-head">
            <span class="section-eyebrow">织识 · HOW IT WORKS</span>
            <h2 class="section-heading">从灵感到作品</h2>
            <p class="section-lede">三步，把散落的文献织成属于你的知识网络。</p>
          </div>
        </RevealOnScroll>

        <!-- 灵感 -->
        <RevealOnScroll :delay="0" direction="up">
          <article class="narration-row">
            <div class="narration-text">
              <span class="narration-index">壹</span>
              <h3 class="narration-title">灵感 · 知识本该相连</h3>
              <p class="narration-body">
                每篇文献都是一根丝线。当它们散落在硬盘与文件夹里，灵感也随之断线。
                织识相信：真正的洞见，诞生于知识彼此相遇的瞬间。
              </p>
            </div>
            <div class="narration-art" aria-hidden="true">
              <svg class="art-spark" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
                <g class="art-rings" stroke="currentColor">
                  <circle cx="100" cy="100" r="42" stroke-width="1" opacity="0.22" />
                  <circle cx="100" cy="100" r="66" stroke-width="0.75" opacity="0.1" />
                </g>
                <g class="art-rays" stroke="currentColor" stroke-linecap="round">
                  <line x1="100" y1="16" x2="100" y2="52" stroke-width="1.5" opacity="0.55" />
                  <line x1="100" y1="148" x2="100" y2="184" stroke-width="1.5" opacity="0.55" />
                  <line x1="16" y1="100" x2="52" y2="100" stroke-width="1.5" opacity="0.55" />
                  <line x1="148" y1="100" x2="184" y2="100" stroke-width="1.5" opacity="0.55" />
                  <line x1="40.6" y1="40.6" x2="66.4" y2="66.4" stroke-width="1" opacity="0.4" />
                  <line x1="133.6" y1="133.6" x2="159.4" y2="159.4" stroke-width="1" opacity="0.4" />
                  <line x1="159.4" y1="40.6" x2="133.6" y2="66.4" stroke-width="1" opacity="0.4" />
                  <line x1="66.4" y1="133.6" x2="40.6" y2="159.4" stroke-width="1" opacity="0.4" />
                </g>
                <circle class="art-core" cx="100" cy="100" r="6" fill="currentColor" />
                <circle class="art-pulse" cx="100" cy="100" r="6" stroke="currentColor" stroke-width="1" />
              </svg>
            </div>
          </article>
        </RevealOnScroll>

        <!-- 方法 -->
        <RevealOnScroll :delay="150" direction="up">
          <article class="narration-row reverse">
            <div class="narration-text">
              <span class="narration-index">贰</span>
              <h3 class="narration-title">方法 · 以 AI 织网</h3>
              <p class="narration-body">
                上传论文后，AI 自动提取核心概念、识别它们之间的关系，
                织成一张会生长的知识网络。你可以随时增删概念、编辑关系，让网络长成你自己的样子。
              </p>
            </div>
            <div class="narration-art" aria-hidden="true">
              <svg class="art-network" viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
                <g class="art-edges" stroke="currentColor">
                  <line x1="40" y1="40" x2="96" y2="34" stroke-width="1" opacity="0.35" />
                  <line x1="96" y1="34" x2="158" y2="46" stroke-width="1" opacity="0.35" />
                  <line x1="40" y1="40" x2="96" y2="118" stroke-width="1" opacity="0.35" />
                  <line x1="158" y1="46" x2="96" y2="118" stroke-width="1" opacity="0.35" />
                  <line x1="40" y1="40" x2="158" y2="46" stroke-width="1" opacity="0.18" />
                  <line x1="96" y1="34" x2="96" y2="118" stroke-width="1" opacity="0.3" />
                  <line x1="40" y1="120" x2="96" y2="118" stroke-width="1" opacity="0.2" />
                  <line x1="158" y1="120" x2="96" y2="118" stroke-width="1" opacity="0.2" />
                </g>
                <g class="art-nodes" fill="currentColor">
                  <circle class="node" cx="40" cy="40" r="4" opacity="0.8" />
                  <circle class="node node-hero" cx="96" cy="34" r="6" />
                  <circle class="node" cx="158" cy="46" r="4" opacity="0.8" />
                  <circle class="node" cx="96" cy="118" r="4" opacity="0.8" />
                  <circle class="node" cx="40" cy="120" r="3" opacity="0.6" />
                  <circle class="node" cx="158" cy="120" r="3" opacity="0.6" />
                </g>
              </svg>
            </div>
          </article>
        </RevealOnScroll>

        <!-- 作品 -->
        <RevealOnScroll :delay="300" direction="up">
          <article class="narration-row">
            <div class="narration-text">
              <span class="narration-index">叁</span>
              <h3 class="narration-title">作品 · 让知识成为作品</h3>
              <p class="narration-body">
                从一篇到多篇，从散点到系统。每一次织补都让知识网更完整。
                走进知识库，在全局探索中，遇见跨文献的洞见。
              </p>
              <button class="btn-primary narration-cta" @click="goLibrary">进入知识库</button>
            </div>
            <div class="narration-art" aria-hidden="true">
              <svg class="art-work" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
                <g class="art-threads" stroke="currentColor">
                  <line class="thread" x1="50" y1="20" x2="50" y2="180" stroke-width="1" />
                  <line class="thread" x1="100" y1="20" x2="100" y2="180" stroke-width="1" />
                  <line class="thread" x1="150" y1="20" x2="150" y2="180" stroke-width="1" />
                  <line class="thread" x1="20" y1="50" x2="180" y2="50" stroke-width="1" />
                  <line class="thread" x1="20" y1="100" x2="180" y2="100" stroke-width="1" />
                  <line class="thread" x1="20" y1="150" x2="180" y2="150" stroke-width="1" />
                </g>
                <g class="art-weave" fill="currentColor">
                  <circle cx="50" cy="50" r="3.5" />
                  <circle cx="100" cy="50" r="3.5" />
                  <circle cx="150" cy="50" r="3.5" />
                  <circle cx="50" cy="100" r="3.5" />
                  <circle class="node-hero" cx="100" cy="100" r="5" />
                  <circle cx="150" cy="100" r="3.5" />
                  <circle cx="50" cy="150" r="3.5" />
                  <circle cx="100" cy="150" r="3.5" />
                  <circle cx="150" cy="150" r="3.5" />
                </g>
              </svg>
            </div>
          </article>
        </RevealOnScroll>
      </div>
    </section>

    <!-- ══════════ 最近论文 ══════════ -->
    <section class="recent-section">
      <div class="container">
        <RevealOnScroll :delay="0" direction="up">
          <div class="recent-head">
            <div>
              <span class="section-eyebrow">织识 · RECENT</span>
              <h2 class="section-heading">最近织就</h2>
            </div>
            <button class="btn-import" @click="goImport">
              <span class="btn-plus">+</span>上传论文
            </button>
          </div>
        </RevealOnScroll>

        <div class="recent-grid" v-if="recentPapers.length">
          <RevealOnScroll v-for="(p, i) in recentPapers" :key="p.id" :delay="i * 100" direction="up">
            <div class="paper-card glass-panel" @click="openPaper(p)">
              <div class="paper-icon">📄</div>
              <div class="paper-info">
                <h4>{{ p.title }}</h4>
                <span>{{ p.page_count }} 页 · {{ p.concept_count || 0 }} 概念 · {{ p.upload_time?.slice(0, 10) }}</span>
              </div>
              <SealBadge :status="p.extract_status" />
            </div>
          </RevealOnScroll>
        </div>

        <div class="empty-state" v-else-if="!loading">
          <span class="empty-glyph">织</span>
          <p class="empty-text">知识库还空着 —— 上传第一篇文献，开始编织你的知识网</p>
          <button class="btn-primary" @click="goImport">
            <span class="btn-plus">+</span>上传论文
          </button>
        </div>
      </div>
    </section>

    <!-- ══════════ Footer ══════════ -->
    <footer class="home-footer">
      <span class="footer-mark">织</span>
      <span class="footer-text">织识 · 把知识织成网络</span>
    </footer>
  </div>
</template>

<script setup>
import { Document, Aim, Connection, Key } from '@element-plus/icons-vue'
import { getSettings } from '@/api'
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLibraryStore } from '@/stores/library'
import ParticleBackground from '@/components/ParticleBackground.vue'
import CountUp from '@/components/motion/CountUp.vue'
import RevealOnScroll from '@/components/motion/RevealOnScroll.vue'
import SealBadge from '@/components/motion/SealBadge.vue'

const router = useRouter()
const lib = useLibraryStore()

const loading = ref(true)
const statCards = ref([
  { label: '论文总数', value: 0, icon: Document, accent: 'accent-cyan' },
  { label: '核心概念', value: 0, icon: Aim, accent: 'accent-vermilion' },
  { label: '知识关系', value: 0, icon: Connection, accent: 'accent-amber' },
])
const recentPapers = ref([])
const needsKey = ref(false)   // BYOK：未配置 API Key 时的引导提示

onMounted(async () => {
  // BYOK 引导：未配置 Key 时顶部提示（配置后自动消失）
  try {
    const s = await getSettings()
    needsKey.value = !s.hasKey
  } catch { /* 非关键路径 */ }
  await lib.fetchStats()
  statCards.value[0].value = lib.stats.paperCount || 0
  statCards.value[1].value = lib.stats.conceptCount || 0
  statCards.value[2].value = lib.stats.relationCount || 0
  await lib.fetchPapers()
  recentPapers.value = lib.papers.slice(0, 5)
  loading.value = false
})

function goImport() {
  router.push({ name: 'Import' })
}

function goLibrary() {
  router.push({ name: 'Library' })
}

function openPaper(p) {
  router.push({ name: 'Workbench', params: { paperId: p.id } })
}
</script>

<style scoped>
/* ═══════════════════ 根容器 ═══════════════════ */
.home-page {
  --page-accent: var(--page-home-accent);
  position: relative;
  isolation: isolate;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
}

.container {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 var(--space-2xl);
}

/* ═══════════════════ Hero ═══════════════════ */
.hero {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  overflow: hidden;
  padding: var(--space-2xl) var(--space-lg);
  min-height: calc(100vh - var(--header-height));
  min-height: calc(100svh - var(--header-height));
}

.hero-halo {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 50% 42%, rgba(232, 69, 60, 0.18) 0%, transparent 44%),
    radial-gradient(circle at 50% 42%, rgba(232, 69, 60, 0.07) 0%, transparent 64%),
    radial-gradient(circle at 12% 18%, rgba(232, 69, 60, 0.05) 0%, transparent 40%);
  animation: halo-breathe 7s ease-in-out infinite;
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 720px;
}

.hero-content > * {
  animation: hero-in 0.7s var(--ease-out-soft) both;
}
.hero-eyebrow { animation-delay: 0.05s; }
.hero-mark { animation-delay: 0.15s; }
.hero-subtitle { animation-delay: 0.28s; }
.hero-desc { animation-delay: 0.38s; }
.hero-actions { animation-delay: 0.5s; }

.hero-eyebrow {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.5em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: var(--space-lg);
}

.hero-mark {
  line-height: 1;
  margin: 0;
}

.hero-char {
  display: inline-block;
  font-family: var(--font-display);
  font-size: clamp(120px, 22vw, 240px);
  font-weight: 700;
  line-height: 1;
  color: #ff6a60;
  user-select: none;
  text-shadow:
    0 0 24px rgba(232, 69, 60, 0.55),
    0 0 80px rgba(232, 69, 60, 0.35),
    0 0 180px rgba(232, 69, 60, 0.18);
  animation: char-float 6s ease-in-out infinite;
}

.hero-subtitle {
  font-family: var(--font-display);
  font-size: clamp(20px, 3.4vw, 32px);
  font-weight: 600;
  color: var(--text-primary);
  margin-top: var(--space-lg);
  letter-spacing: 0.08em;
}

.hero-desc {
  font-size: var(--text-base);
  color: var(--text-muted);
  margin: var(--space-sm) auto 0;
  max-width: 520px;
  line-height: 1.9;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-md);
  margin-top: var(--space-xl);
}

/* 按钮 */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 32px;
  background: var(--vermilion);
  border: 1px solid var(--vermilion);
  border-radius: var(--radius-md);
  color: #fff;
  font-size: var(--text-md);
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  box-shadow: var(--vermilion-glow);
  transition: transform var(--ease-out), box-shadow var(--ease-out), background var(--ease-out);
}
.btn-primary:hover {
  background: var(--vermilion-hover);
  box-shadow: 0 0 26px rgba(232, 69, 60, 0.55);
  transform: translateY(-2px);
}
.btn-primary:active { transform: translateY(0); }
.btn-plus { font-size: 20px; font-weight: 300; line-height: 1; }

.btn-ghost {
  display: inline-flex;
  align-items: center;
  padding: 12px 28px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-md);
  font-family: inherit;
  text-decoration: none;
  transition: all var(--ease-out);
}
.btn-ghost:hover {
  border-color: var(--vermilion);
  color: var(--vermilion);
  background: var(--vermilion-bg);
}

/* 向下探索指示 */
.hero-scroll {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: var(--text-xs);
  letter-spacing: 0.25em;
}
.scroll-line {
  width: 1px;
  height: 38px;
  background: linear-gradient(to bottom, transparent, var(--vermilion));
  animation: scroll-drop 2.4s ease-in-out infinite;
}
.scroll-text { font-family: var(--font-mono); }

/* ═══════════════════ 通用分区标题 ═══════════════════ */
.section-head {
  margin-bottom: var(--space-xl);
}
.section-head.stats-head {
  text-align: center;
}
.section-eyebrow {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.35em;
  text-transform: uppercase;
  color: var(--vermilion);
  margin-bottom: var(--space-sm);
}
.section-heading {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.05em;
}
.section-lede {
  font-size: var(--text-base);
  color: var(--text-muted);
  margin-top: var(--space-sm);
  max-width: 46ch;
  line-height: 1.8;
}

/* ═══════════════════ 统计区 ═══════════════════ */
.stats-section {
  position: relative;
  z-index: 1;
  padding: var(--space-xl) 0 var(--space-xl);
}
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
}
.stats-row :deep(.reveal) { height: 100%; }
.stat-card {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-lg);
  height: 100%;
  cursor: default;
}
.stat-icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
}
.stat-icon.accent-cyan { color: var(--cyan); background: var(--cyan-bg); border-color: rgba(0, 212, 255, 0.2); }
.stat-icon.accent-vermilion { color: var(--vermilion); background: var(--vermilion-bg); border-color: rgba(232, 69, 60, 0.22); }
.stat-icon.accent-amber { color: var(--amber); background: var(--amber-bg); border-color: rgba(245, 158, 11, 0.2); }
.stat-value {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
}
.stat-label {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-top: 4px;
  letter-spacing: 0.02em;
}

/* ═══════════════════ 叙事区 ═══════════════════ */
.narrative-section {
  position: relative;
  z-index: 1;
  padding: var(--space-xl) 0 var(--space-2xl);
}
.narration-row {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  grid-template-areas: 'text art';
  align-items: center;
  gap: var(--space-2xl);
  padding: var(--space-2xl) 0;
  border-top: 1px solid var(--border-subtle);
}
.narration-row.reverse {
  grid-template-areas: 'art text';
}
.narration-text { grid-area: text; }
.narration-art { grid-area: art; }

.narration-index {
  display: inline-block;
  font-family: var(--font-display);
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--vermilion);
  line-height: 1;
  margin-bottom: var(--space-md);
}
.narration-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.05em;
  margin-bottom: var(--space-md);
}
.narration-body {
  font-size: var(--text-base);
  color: var(--text-secondary);
  line-height: 1.95;
  max-width: 46ch;
}
.narration-cta {
  margin-top: var(--space-lg);
}

.narration-art {
  color: var(--vermilion);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
}
.narration-art svg {
  width: 100%;
  max-width: 250px;
  height: auto;
  overflow: visible;
}

/* ── 叙事 SVG 动效（仅 opacity/transform） ── */
.art-pulse {
  transform-box: fill-box;
  transform-origin: center;
  animation: spark-pulse 2.6s ease-in-out infinite;
}
.art-rays {
  transform-box: fill-box;
  transform-origin: center;
  animation: spark-spin 36s linear infinite;
}
.art-nodes .node,
.art-weave circle {
  animation: node-glow 3.2s ease-in-out infinite;
}
.art-nodes .node:nth-child(2) { animation-delay: 0.4s; }
.art-nodes .node:nth-child(3) { animation-delay: 0.8s; }
.art-nodes .node:nth-child(4) { animation-delay: 1.2s; }
.art-nodes .node:nth-child(5) { animation-delay: 1.6s; }
.art-nodes .node:nth-child(6) { animation-delay: 2s; }
.art-weave circle:nth-child(5) { animation-delay: 0.6s; }

/* ═══════════════════ 最近论文 ═══════════════════ */
.recent-section {
  position: relative;
  z-index: 1;
  padding: var(--space-2xl) 0 var(--space-2xl);
}
.recent-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
}
.recent-head .section-heading { margin-bottom: 0; }

.btn-import {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  border: 1px solid var(--vermilion);
  border-radius: var(--radius-md);
  background: var(--vermilion-bg);
  color: var(--vermilion);
  font-size: var(--text-sm);
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--ease-out);
}
.btn-import:hover {
  background: var(--vermilion);
  color: #fff;
  box-shadow: var(--vermilion-glow);
  transform: translateY(-1px);
}

.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-md);
}
.recent-grid :deep(.reveal) { height: 100%; }
.paper-card {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  height: 100%;
  cursor: pointer;
  transition: border-color var(--ease-out), box-shadow var(--ease-out), transform var(--ease-out);
}
.paper-card:hover {
  border-color: var(--vermilion);
  box-shadow: 0 0 18px rgba(232, 69, 60, 0.12);
  transform: translateY(-2px);
}
.paper-icon { font-size: 24px; flex-shrink: 0; }
.paper-info { flex: 1; min-width: 0; }
.paper-info h4 {
  font-size: var(--text-md);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.paper-info span {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: 4px;
}

/* 空态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  padding: var(--space-2xl) var(--space-lg);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-lg);
  text-align: center;
}
.empty-glyph {
  font-family: var(--font-display);
  font-size: 44px;
  color: var(--vermilion);
  opacity: 0.7;
  line-height: 1;
}
.empty-text {
  color: var(--text-muted);
  font-size: var(--text-md);
  max-width: 40ch;
  line-height: 1.8;
}

/* ═══════════════════ Footer ═══════════════════ */
.home-footer {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-xl) var(--space-lg) var(--space-2xl);
  border-top: 1px solid var(--border-subtle);
  color: var(--text-muted);
  font-size: var(--text-sm);
  letter-spacing: 0.12em;
}
.footer-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: var(--vermilion);
  color: #fff;
  font-family: var(--font-display);
  font-size: 13px;
  border-radius: var(--radius-sm);
  box-shadow: var(--vermilion-glow);
}

/* ═══════════════════ 关键帧 ═══════════════════ */
@keyframes hero-in {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes halo-breathe {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}
@keyframes char-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
@keyframes scroll-drop {
  0% { transform: scaleY(0); transform-origin: top; opacity: 0; }
  35% { transform: scaleY(1); transform-origin: top; opacity: 1; }
  65% { transform: scaleY(1); transform-origin: bottom; opacity: 1; }
  100% { transform: scaleY(0); transform-origin: bottom; opacity: 0; }
}
@keyframes spark-pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(2.1); opacity: 0.08; }
}
@keyframes spark-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@keyframes node-glow {
  0%, 100% { opacity: 0.45; }
  50% { opacity: 1; }
}

/* ═══════════════════ 响应式 ═══════════════════ */
@media (max-width: 900px) {
  .narration-row,
  .narration-row.reverse {
    grid-template-columns: 1fr;
    grid-template-areas: 'art' 'text';
    gap: var(--space-lg);
    padding: var(--space-xl) 0;
  }
  .narration-art {
    min-height: 150px;
  }
  .narration-art svg {
    max-width: 200px;
  }
}

@media (max-width: 640px) {
  .container { padding: 0 var(--space-lg); }
  .stats-row {
    grid-template-columns: 1fr;
    gap: var(--space-sm);
  }
  .stat-card {
    padding: var(--space-md);
  }
  .hero {
    justify-content: center;
    padding-top: var(--space-2xl);
  }
  .hero-scroll { display: none; }
  .recent-head {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-md);
  }
  .recent-grid {
    grid-template-columns: 1fr;
  }
  .hero-char {
    font-size: clamp(96px, 34vw, 150px);
  }
}

/* ═══════════════════ 减弱动效 ═══════════════════ */
@media (prefers-reduced-motion: reduce) {
  .hero-halo,
  .hero-char,
  .hero-scroll .scroll-line,
  .narration-art * {
    animation: none !important;
  }
  .hero-content > * {
    animation: none !important;
  }
  .home-page { scroll-behavior: auto; }
}

/* BYOK 未配置引导条 */
.byok-banner {
  position: relative;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  margin: var(--space-md) auto 0;
  width: fit-content;
  max-width: calc(100% - 48px);
  padding: 8px 18px;
  border: 1px solid var(--amber);
  border-radius: var(--radius-lg);
  background: var(--amber-bg);
  color: var(--amber);
  font-size: var(--text-sm);
  text-decoration: none;
  transition: all var(--ease-out);
}
.byok-banner:hover { box-shadow: var(--amber-glow); transform: translateY(-1px); }
</style>