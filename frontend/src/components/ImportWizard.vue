<template>
  <div class="import-wizard">
    <!-- 步骤指示器 -->
    <div class="iw-steps">
      <template v-for="(s, i) in steps" :key="s.key">
        <div class="iw-step" :class="{ active: i === current, done: i < current }">
          <span class="iw-dot">{{ i < current ? '✓' : i + 1 }}</span>
          <span class="iw-label">{{ s.label }}</span>
        </div>
        <span v-if="i < steps.length - 1" class="iw-connector" :class="{ active: i < current }"></span>
      </template>
    </div>

    <!-- 步骤内容 -->
    <div class="iw-body glass-panel">
      <!-- 处理中态 -->
      <div v-if="loading" class="iw-processing">
        <span class="iw-spinner"></span>
        <p class="iw-processing-text">正在提取知识…</p>
      </div>

      <!-- step 0: 上传 PDF -->
      <template v-else-if="current === 0">
        <p class="iw-desc">拖拽或点击上传论文 PDF，AI 将自动提取概念与关系。</p>
        <UploadPanel :uploading="loading" :error="error" @upload="handleUpload" />
      </template>

      <!-- step 1: 粘贴文本 -->
      <template v-else-if="current === 1">
        <label class="input-label">标题</label>
        <input v-model="title" class="dark-input" placeholder="知识标题（可选）" />
        <label class="input-label">内容</label>
        <textarea v-model="text" class="dark-textarea" rows="7" placeholder="粘贴文本..."></textarea>
        <button class="iw-next" :disabled="!text.trim()" @click="handleText">开始提取</button>
      </template>

      <!-- step 2: 网页链接 -->
      <template v-else-if="current === 2">
        <label class="input-label">网页 URL</label>
        <input v-model="url" class="dark-input" placeholder="https://..." @keyup.enter="handleUrl" />
        <button class="iw-next" :disabled="!url.trim()" @click="handleUrl">抓取并提取</button>
      </template>

      <!-- step 3: 手动创建 -->
      <template v-else>
        <label class="input-label">知识主题</label>
        <input v-model="manualTitle" class="dark-input" placeholder="知识主题名称" @keyup.enter="handleManual" />
        <button class="iw-next" :disabled="!manualTitle.trim()" @click="handleManual">创建知识空间</button>
      </template>

      <p v-if="error && !loading" class="iw-error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { uploadPaper, extractFromText, extractFromUrl, createEmptyPaper } from '@/api'
import UploadPanel from '@/components/UploadPanel.vue'

const router = useRouter()

const steps = [
  { key: 'pdf', label: '上传 PDF' },
  { key: 'text', label: '粘贴文本' },
  { key: 'url', label: '网页链接' },
  { key: 'manual', label: '手动创建' },
]

const current = ref(0)
const loading = ref(false)
const error = ref('')

const title = ref('')
const text = ref('')
const url = ref('')
const manualTitle = ref('')

async function go(paperId) {
  router.push({ name: 'Workbench', params: { paperId } })
}

async function handleUpload(file) {
  loading.value = true
  error.value = ''
  try {
    const p = await uploadPaper(file)
    go(p.paper_id)
  } catch (e) {
    error.value = e.message
    loading.value = false
  }
}

async function handleText() {
  if (!text.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const data = await extractFromText(title.value || '文本知识', text.value)
    go(data.paperId)
  } catch (e) {
    error.value = e.message
    loading.value = false
  }
}

async function handleUrl() {
  if (!url.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const data = await extractFromUrl(url.value)
    go(data.paperId)
  } catch (e) {
    error.value = e.message
    loading.value = false
  }
}

async function handleManual() {
  if (!manualTitle.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    const data = await createEmptyPaper(manualTitle.value)
    go(data.paper_id)
  } catch (e) {
    error.value = e.message
    loading.value = false
  }
}
</script>

<style scoped>
.import-wizard {
  width: 100%;
}

/* ── 步骤指示器 ── */
.iw-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: var(--space-xl);
}

.iw-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  min-width: 76px;
}

.iw-dot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--border-strong);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
  font-family: var(--font-mono);
  transition: all var(--ease-out);
}

.iw-step.active .iw-dot {
  border-color: var(--vermilion);
  background: var(--vermilion);
  color: #fff;
  box-shadow: var(--vermilion-glow);
}

.iw-step.done .iw-dot {
  border-color: var(--emerald);
  background: var(--emerald-bg);
  color: var(--emerald);
}

.iw-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  letter-spacing: 0.04em;
  white-space: nowrap;
  transition: color var(--ease-out);
}

.iw-step.active .iw-label { color: var(--vermilion); }
.iw-step.done .iw-label { color: var(--text-secondary); }

.iw-connector {
  flex: 1;
  max-width: 56px;
  height: 1px;
  background: var(--border-default);
  margin: 0 var(--space-sm);
  transform: translateY(-12px);
  transition: background var(--ease-out);
}

.iw-connector.active { background: var(--emerald); }

/* ── 内容区 ── */
.iw-body {
  padding: var(--space-xl);
}

.iw-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-bottom: var(--space-md);
  text-align: center;
}

.iw-processing {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  padding: var(--space-2xl) 0;
}

.iw-spinner {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid var(--border-subtle);
  border-top-color: var(--vermilion);
  animation: iw-spin 0.8s linear infinite;
}

.iw-processing-text {
  font-size: var(--text-md);
  color: var(--text-secondary);
  letter-spacing: 0.06em;
}

@keyframes iw-spin {
  to { transform: rotate(360deg); }
}

/* ── 表单控件 ── */
.input-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: 6px;
  margin-top: var(--space-md);
}
.input-label:first-child { margin-top: 0; }

.dark-input,
.dark-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-primary);
  font-size: var(--text-base);
  font-family: inherit;
  outline: none;
  resize: vertical;
  transition: border-color var(--ease-out), box-shadow var(--ease-out);
}
.dark-input::placeholder,
.dark-textarea::placeholder { color: var(--text-disabled); }
.dark-input:focus,
.dark-textarea:focus {
  border-color: var(--vermilion);
  box-shadow: 0 0 0 2px rgba(232, 69, 60, 0.12);
}

/* ── 下一步按钮 ── */
.iw-next {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  margin-top: var(--space-lg);
  padding: 11px 20px;
  background: var(--vermilion);
  border: 1px solid var(--vermilion);
  border-radius: var(--radius-md);
  color: #fff;
  font-size: var(--text-md);
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  box-shadow: var(--vermilion-glow);
  transition: all var(--ease-out);
}
.iw-next:hover:not(:disabled) {
  background: var(--vermilion-hover);
  transform: translateY(-1px);
}
.iw-next:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

/* ── 错误提示 ── */
.iw-error {
  margin-top: var(--space-md);
  font-size: var(--text-sm);
  color: var(--vermilion);
  text-align: center;
}
</style>
