<template>
  <div class="library-page">
    <div class="library-toolbar">
      <h2 class="page-title">知识库</h2>
      <div class="toolbar-actions">
        <el-input v-model="lib.searchQuery" placeholder="搜索论文..." prefix-icon="Search" clearable style="width:240px" />
        <el-button type="primary" @click="showUpload = true">+ 上传论文</el-button>
      </div>
    </div>

    <div class="paper-grid" v-if="lib.filteredPapers.length">
      <div v-for="p in lib.filteredPapers" :key="p.id" class="paper-card glass-panel" @click="openPaper(p)">
        <div class="pc-header">
          <span class="pc-icon">📄</span>
          <el-dropdown trigger="click" @command="(cmd) => handleAction(cmd, p)">
            <button class="pc-menu-btn" @click.stop>···</button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="open">打开工作台</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <h4 class="pc-title">{{ p.title }}</h4>
        <div class="pc-meta">
          <span>{{ p.page_count }} 页</span>
          <span>{{ p.concept_count || 0 }} 概念</span>
          <span>{{ p.relation_count || 0 }} 关系</span>
        </div>
        <div class="pc-footer">
          <span class="pc-status" :class="p.extract_status">{{ statusMap[p.extract_status] || p.extract_status }}</span>
          <span class="pc-date">{{ p.upload_time?.slice(0, 10) }}</span>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>知识库为空</p>
      <el-button type="primary" @click="showUpload = true">上传第一篇论文</el-button>
    </div>

    <el-dialog v-model="showUpload" title="新建知识" width="560px" destroy-on-close>
      <div class="input-mode-tabs">
        <button v-for="m in inputModes" :key="m.key"
          class="mode-tab" :class="{ active: inputMode === m.key }"
          @click="inputMode = m.key">
          <span class="mode-icon">{{ m.icon }}</span><span>{{ m.label }}</span>
        </button>
      </div>
      <div v-if="inputMode === 'pdf'" class="mode-panel">
        <UploadPanel :uploading="uploading" :error="uploadError" @upload="handleUpload" />
      </div>
      <div v-if="inputMode === 'text'" class="mode-panel">
        <label class="input-label">知识标题</label>
        <input v-model="textTitle" class="dark-input" placeholder="输入标题（可选）" />
        <label class="input-label">文本内容</label>
        <textarea v-model="textContent" class="dark-textarea" rows="6" placeholder="粘贴文本内容..."></textarea>
        <el-button type="primary" @click="handleTextExtract" :loading="uploading" :disabled="!textContent.trim()" style="width:100%;margin-top:12px">开始提取</el-button>
      </div>
      <div v-if="inputMode === 'url'" class="mode-panel">
        <label class="input-label">网页 URL</label>
        <input v-model="urlInput" class="dark-input" placeholder="https://..." @keyup.enter="handleUrlExtract" />
        <el-button type="primary" @click="handleUrlExtract" :loading="uploading" :disabled="!urlInput.trim()" style="width:100%;margin-top:12px">抓取并提取</el-button>
      </div>
      <div v-if="inputMode === 'manual'" class="mode-panel">
        <label class="input-label">知识主题</label>
        <input v-model="manualTitle" class="dark-input" placeholder="输入知识主题名称" @keyup.enter="handleManualCreate" />
        <el-button type="primary" @click="handleManualCreate" :disabled="!manualTitle.trim()" style="width:100%;margin-top:12px">创建知识空间</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useLibraryStore } from '@/stores/library'
import { uploadPaper, extractFromText, extractFromUrl, createEmptyPaper } from '@/api'
import UploadPanel from '@/components/UploadPanel.vue'

const router = useRouter()
const lib = useLibraryStore()

const showUpload = ref(false)
const uploading = ref(false)
const uploadError = ref('')
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
const statusMap = { done: '已提取', pending: '待提取', processing: '提取中', failed: '失败' }

onMounted(() => lib.fetchPapers())

function openPaper(p) {
  router.push({ name: 'Workbench', params: { paperId: p.id } })
}

async function handleAction(cmd, p) {
  if (cmd === 'open') openPaper(p)
  if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm(`确定删除「${p.title}」？`, '删除确认', { type: 'warning' })
      await lib.removePaper(p.id)
    } catch (_) { /* cancelled */ }
  }
}

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
</script>

<style scoped>
.library-page {
  height: 100%; overflow-y: auto;
  padding: var(--space-xl) var(--space-2xl);
}
.library-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: var(--space-xl);
}
.page-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  color: var(--text-primary);
}
.toolbar-actions { display: flex; gap: var(--space-md); align-items: center; }
.paper-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-md);
}
.paper-card {
  padding: var(--space-lg);
  cursor: pointer;
  transition: all var(--ease-out);
}
.paper-card:hover { border-color: var(--vermilion); }
.pc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-sm); }
.pc-icon { font-size: 28px; }
.pc-menu-btn { background: none; border: none; color: var(--text-muted); font-size: 16px; cursor: pointer; padding: 0 4px; }
.pc-menu-btn:hover { color: var(--text-primary); }
.pc-title {
  font-size: var(--text-md); color: var(--text-primary);
  margin-bottom: var(--space-sm);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.pc-meta { display: flex; gap: var(--space-md); margin-bottom: var(--space-md); }
.pc-meta span { font-size: var(--text-xs); color: var(--text-muted); }
.pc-footer { display: flex; justify-content: space-between; align-items: center; }
.pc-status { font-size: var(--text-xs); padding: 2px 8px; border-radius: 10px; background: rgba(255,255,255,0.05); color: var(--text-muted); }
.pc-status.done { color: var(--emerald); background: var(--emerald-bg); }
.pc-status.failed { color: var(--vermilion); background: var(--vermilion-bg); }
.pc-date { font-size: var(--text-xs); color: var(--text-muted); }
.empty-state { text-align: center; padding: var(--space-3xl); color: var(--text-muted); }
.empty-state p { margin-bottom: var(--space-md); }

.input-mode-tabs { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-sm); margin-bottom: var(--space-lg); }
.mode-tab { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: var(--space-md); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: transparent; color: var(--text-muted); font-size: var(--text-xs); font-family: inherit; cursor: pointer; transition: all var(--ease-out); }
.mode-tab:hover { border-color: var(--border-strong); color: var(--text-primary); }
.mode-tab.active { border-color: var(--vermilion); color: var(--vermilion); background: var(--vermilion-bg); }
.mode-icon { font-size: 20px; }
.mode-panel { min-height: 120px; }
.input-label { display: block; font-size: var(--text-xs); color: var(--text-muted); margin-bottom: 6px; margin-top: var(--space-md); }
.input-label:first-child { margin-top: 0; }
.dark-input, .dark-textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: rgba(255,255,255,0.04); color: var(--text-primary); font-size: var(--text-base); font-family: inherit; outline: none; resize: vertical; }
.dark-input:focus, .dark-textarea:focus { border-color: var(--vermilion); }
</style>
