<template>
  <div class="home-dashboard">
    <ParticleBackground />

    <!-- 英雄区 -->
    <section class="hero">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <h1 class="hero-title">
          <span class="hero-mark">织</span>识
        </h1>
        <p class="hero-subtitle">将文献编织为知识网络</p>
        <p class="hero-desc">AI 驱动的学术知识重构引擎 — 上传论文，发现知识脉络</p>
        <button class="hero-upload-btn" @click="showUpload = true">
          <span>+</span> 上传论文开始
        </button>
      </div>
    </section>

    <!-- 统计卡片 -->
    <section class="stats-row">
      <div class="stat-card glass-panel" v-for="s in statCards" :key="s.label">
        <div class="stat-icon" :class="s.accent">{{ s.icon }}</div>
        <div class="stat-body">
          <span class="stat-value">{{ s.value }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- 最近论文 -->
    <section class="recent-section" v-if="recentPapers.length">
      <h2 class="section-title">最近上传</h2>
      <div class="recent-grid">
        <div
          v-for="p in recentPapers" :key="p.id"
          class="paper-card glass-panel"
          @click="openPaper(p)"
        >
          <div class="paper-icon">📄</div>
          <div class="paper-info">
            <h4>{{ p.title }}</h4>
            <span>{{ p.page_count }} 页 · {{ p.concept_count || 0 }} 概念 · {{ p.upload_time?.slice(0, 10) }}</span>
          </div>
          <span class="paper-status" :class="p.extract_status">
            {{ statusMap[p.extract_status] || p.extract_status }}
          </span>
        </div>
      </div>
    </section>

    <!-- 空态 -->
    <section class="empty-section" v-else-if="!loading">
      <p class="empty-text">知识库为空，上传第一篇论文开始构建知识体系</p>
    </section>

    <!-- 新建对话框：多模式 -->
    <el-dialog v-model="showUpload" title="新建知识" width="560px" destroy-on-close>
      <!-- 输入模式切换 -->
      <div class="input-mode-tabs">
        <button v-for="m in inputModes" :key="m.key"
          class="mode-tab" :class="{ active: inputMode === m.key }"
          @click="inputMode = m.key">
          <span class="mode-icon">{{ m.icon }}</span>
          <span>{{ m.label }}</span>
        </button>
      </div>

      <!-- PDF 上传 -->
      <div v-if="inputMode === 'pdf'" class="mode-panel">
        <UploadPanel :uploading="uploading" :error="uploadError" @upload="handleUpload" />
      </div>

      <!-- 粘贴文本 -->
      <div v-if="inputMode === 'text'" class="mode-panel">
        <label class="input-label">知识标题</label>
        <input v-model="textTitle" class="dark-input" placeholder="输入标题（可选）" />
        <label class="input-label">文本内容</label>
        <textarea v-model="textContent" class="dark-textarea" rows="8"
          placeholder="粘贴论文摘要、文章内容、笔记... AI 将自动提取核心概念和关系"></textarea>
        <el-button type="primary" @click="handleTextExtract" :loading="uploading" :disabled="!textContent.trim()"
          style="width:100%;margin-top:12px">
          开始提取知识
        </el-button>
      </div>

      <!-- 网页链接 -->
      <div v-if="inputMode === 'url'" class="mode-panel">
        <label class="input-label">网页 URL</label>
        <input v-model="urlInput" class="dark-input" placeholder="https://..." @keyup.enter="handleUrlExtract" />
        <el-button type="primary" @click="handleUrlExtract" :loading="uploading" :disabled="!urlInput.trim()"
          style="width:100%;margin-top:12px">
          抓取并提取知识
        </el-button>
      </div>

      <!-- 手动创建 -->
      <div v-if="inputMode === 'manual'" class="mode-panel">
        <label class="input-label">知识主题</label>
        <input v-model="manualTitle" class="dark-input" placeholder="输入知识主题名称" @keyup.enter="handleManualCreate" />
        <p class="mode-hint">创建空白知识空间，手动添加概念和关系，构建你自己的知识体系</p>
        <el-button type="primary" @click="handleManualCreate" :disabled="!manualTitle.trim()"
          style="width:100%;margin-top:12px">
          创建知识空间
        </el-button>
      </div>

      <div v-if="uploading" style="margin-top: 16px">
        <el-progress :percentage="100" :indeterminate="true" :stroke-width="4" />
        <p style="text-align:center;color:var(--text-muted);margin-top:8px;font-size:13px">
          AI 正在提取知识结构...
        </p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLibraryStore } from '@/stores/library'
import { uploadPaper, extractFromText, extractFromUrl, createEmptyPaper } from '@/api'
import UploadPanel from '@/components/UploadPanel.vue'
import ParticleBackground from '@/components/ParticleBackground.vue'

const router = useRouter()
const lib = useLibraryStore()

const loading = ref(true)
const showUpload = ref(false)
const uploading = ref(false)
const uploadError = ref('')

// 多模式输入
const inputMode = ref('pdf')
const textTitle = ref('')
const textContent = ref('')
const urlInput = ref('')
const manualTitle = ref('')
const inputModes = [
  { key: 'pdf', label: '上传 PDF', icon: '📄' },
  { key: 'text', label: '粘贴文本', icon: '📝' },
  { key: 'url', label: '网页链接', icon: '🔗' },
  { key: 'manual', label: '手动创建', icon: '✏️' },
]

const statCards = ref([
  { label: '论文总数', value: 0, icon: '▣', accent: 'accent-cyan' },
  { label: '核心概念', value: 0, icon: '◎', accent: 'accent-vermilion' },
  { label: '知识关系', value: 0, icon: '◆', accent: 'accent-amber' },
])

const recentPapers = ref([])

const statusMap = { done: '已提取', pending: '待提取', processing: '提取中', failed: '失败' }

onMounted(async () => {
  await lib.fetchStats()
  statCards.value[0].value = lib.stats.paperCount || 0
  statCards.value[1].value = lib.stats.conceptCount || 0
  statCards.value[2].value = lib.stats.relationCount || 0
  await lib.fetchPapers()
  recentPapers.value = lib.papers.slice(0, 5)
  loading.value = false
})

async function handleUpload(file) {
  uploading.value = true
  uploadError.value = ''
  try {
    const paper = await uploadPaper(file)
    showUpload.value = false
    router.push({ name: 'Workbench', params: { paperId: paper.paper_id } })
  } catch (e) {
    uploadError.value = e.message
  } finally {
    uploading.value = false
  }
}

async function handleTextExtract() {
  if (!textContent.value.trim()) return
  uploading.value = true; uploadError.value = ''
  try {
    const data = await extractFromText(textTitle.value || '文本知识', textContent.value)
    showUpload.value = false
    router.push({ name: 'Workbench', params: { paperId: data.paperId } })
  } catch (e) { uploadError.value = e.message } finally { uploading.value = false }
}

async function handleUrlExtract() {
  if (!urlInput.value.trim()) return
  uploading.value = true; uploadError.value = ''
  try {
    const data = await extractFromUrl(urlInput.value)
    showUpload.value = false
    router.push({ name: 'Workbench', params: { paperId: data.paperId } })
  } catch (e) { uploadError.value = e.message } finally { uploading.value = false }
}

async function handleManualCreate() {
  if (!manualTitle.value.trim()) return
  try {
    const data = await createEmptyPaper(manualTitle.value)
    showUpload.value = false
    router.push({ name: 'Workbench', params: { paperId: data.paper_id } })
  } catch (e) { uploadError.value = e.message }
}

function openPaper(p) {
  router.push({ name: 'Workbench', params: { paperId: p.id } })
}
</script>

<style scoped>
.home-dashboard {
  --page-accent: var(--page-home-accent);
  height: 100%;
  overflow-y: auto;
  padding: var(--space-xl) var(--space-2xl);
}

/* 英雄区 */
.hero {
  position: relative;
  text-align: center;
  padding: var(--space-2xl) 0;
  margin-bottom: var(--space-xl);
}
.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 30%, rgba(232,69,60,0.08) 0%, transparent 60%),
    radial-gradient(circle at 20% 60%, rgba(0,212,255,0.05) 0%, transparent 50%);
  pointer-events: none;
}
.hero-content { position: relative; z-index: 1; }
.hero-mark {
  display: inline-block;
  width: 56px; height: 56px;
  line-height: 56px;
  background: var(--vermilion);
  color: #fff;
  font-family: var(--font-display);
  font-size: 30px; font-weight: 700;
  border-radius: var(--radius-md);
  box-shadow: var(--vermilion-glow);
  animation: mark-pulse 3s ease-in-out infinite;
}
@keyframes mark-pulse {
  0%, 100% { box-shadow: 0 0 16px rgba(232,69,60,0.35); }
  50% { box-shadow: 0 0 32px rgba(232,69,60,0.55); }
}
.hero-title {
  font-family: var(--font-display);
  font-size: var(--text-3xl);
  color: var(--text-primary);
  margin-top: var(--space-lg);
}
.hero-subtitle {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  margin-top: var(--space-sm);
}
.hero-desc {
  font-size: var(--text-base);
  color: var(--text-muted);
  margin-top: var(--space-sm);
}
.hero-upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: var(--space-lg);
  padding: 10px 28px;
  border: 1px solid var(--vermilion);
  border-radius: var(--radius-md);
  background: var(--vermilion);
  color: #fff;
  font-size: var(--text-md);
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: all var(--ease-out);
}
.hero-upload-btn:hover {
  box-shadow: var(--vermilion-glow);
  transform: translateY(-1px);
}
.hero-upload-btn span { font-size: 20px; font-weight: 300; }

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
}
.stat-card {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-lg);
  cursor: default;
}
.stat-icon {
  width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.04);
}
.stat-icon.accent-cyan { color: var(--cyan); }
.stat-icon.accent-vermilion { color: var(--vermilion); }
.stat-icon.accent-amber { color: var(--amber); }
.stat-value {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
}
.stat-label {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-top: 2px;
}

/* 最近论文 */
.section-title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--text-primary);
  margin-bottom: var(--space-md);
}
.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-md);
}
.paper-card {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  cursor: pointer;
  transition: all var(--ease-out);
}
.paper-card:hover {
  border-color: var(--vermilion);
  box-shadow: 0 0 16px rgba(232,69,60,0.10);
}
.paper-icon { font-size: 24px; }
.paper-info { flex: 1; min-width: 0; }
.paper-info h4 {
  font-size: var(--text-md);
  color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.paper-info span {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.paper-status {
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(255,255,255,0.05);
  color: var(--text-muted);
  flex-shrink: 0;
}
.paper-status.done { color: var(--emerald); background: var(--emerald-bg); }
.paper-status.failed { color: var(--vermilion); background: var(--vermilion-bg); }

/* 空态 */
.empty-section {
  text-align: center;
  padding: var(--space-2xl);
}
.empty-text { color: var(--text-muted); font-size: var(--text-md); }

/* 输入模式标签 */
.input-mode-tabs {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-sm);
  margin-bottom: var(--space-lg);
}
.mode-tab {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: var(--space-md); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: transparent; color: var(--text-muted);
  font-size: var(--text-xs); font-family: inherit; cursor: pointer;
  transition: all var(--ease-out);
}
.mode-tab:hover { border-color: var(--border-strong); color: var(--text-primary); }
.mode-tab.active { border-color: var(--vermilion); color: var(--vermilion); background: var(--vermilion-bg); }
.mode-icon { font-size: 20px; }
.mode-panel { min-height: 160px; }
.input-label { display: block; font-size: var(--text-xs); color: var(--text-muted); margin-bottom: 6px; margin-top: var(--space-md); }
.input-label:first-child { margin-top: 0; }
.dark-input, .dark-textarea {
  width: 100%; padding: 10px 12px;
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  background: rgba(255,255,255,0.04); color: var(--text-primary);
  font-size: var(--text-base); font-family: inherit; outline: none; resize: vertical;
}
.dark-input:focus, .dark-textarea:focus { border-color: var(--vermilion); }
.mode-hint { font-size: var(--text-sm); color: var(--text-muted); margin-top: var(--space-md); line-height: 1.6; }
</style>
