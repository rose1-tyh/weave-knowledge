<template>
  <div class="library-page">
    <div class="library-toolbar">
      <h2 class="page-title">知识库</h2>
      <div class="toolbar-actions">
        <el-input v-model="lib.searchQuery" placeholder="搜索论文..." prefix-icon="Search" clearable style="width:240px" />
        <el-button type="primary" @click="router.push('/import')">+ 上传论文</el-button>
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
      <el-button type="primary" @click="router.push('/import')">上传第一篇论文</el-button>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useLibraryStore } from '@/stores/library'

const router = useRouter()
const lib = useLibraryStore()

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
</script>

<style scoped>
.library-page {
  --page-accent: var(--page-library-accent);
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
</style>
