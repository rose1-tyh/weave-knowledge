<template>
  <div class="library-page">
    <div class="library-toolbar">
      <h2 class="page-title">知识库</h2>
      <div class="toolbar-actions">
        <el-input v-model="lib.searchQuery" placeholder="搜索论文..." prefix-icon="Search" clearable style="width:240px" />
        <el-button type="primary" @click="router.push('/import')">+ 上传论文</el-button>
      </div>
    </div>

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="paper-grid skeleton-grid" aria-label="知识库加载中">
      <SkeletonBlock v-for="n in 6" :key="n" height="160px" />
    </div>

    <!-- 错落瀑布流卡片 -->
    <div v-else-if="lib.filteredPapers.length" class="paper-grid">
      <div v-for="p in lib.filteredPapers" :key="p.id" class="paper-card glass-panel" @click="openPaper(p)">
        <span class="pc-seal" aria-hidden="true">织</span>
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
          <SealBadge :status="p.extract_status" />
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
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useLibraryStore } from '@/stores/library'
import SealBadge from '@/components/motion/SealBadge.vue'
import SkeletonBlock from '@/components/motion/SkeletonBlock.vue'

const router = useRouter()
const lib = useLibraryStore()

const loading = ref(true)

onMounted(async () => {
  try {
    await lib.fetchPapers()
  } catch (_) {
    /* 拉取失败则保留空列表 */
  } finally {
    loading.value = false
  }
})

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

/* ── 错落瀑布流 ── */
.paper-grid {
  columns: 3 260px;
  column-gap: var(--space-md);
}
.paper-card {
  position: relative;
  overflow: hidden;
  padding: var(--space-lg);
  margin-bottom: var(--space-md);
  break-inside: avoid;
  cursor: pointer;
  transition: transform var(--ease-out-soft), border-color var(--ease-out-soft), box-shadow var(--ease-out-soft);
}
.paper-card:hover {
  transform: translateY(-4px);
  border-color: var(--page-library-accent);
  box-shadow: 0 0 24px rgba(0, 212, 255, 0.12);
}

/* ── hover 织字印章（仅 opacity/transform 动效） ── */
.pc-seal {
  position: absolute;
  right: -14px; bottom: -16px;
  width: 84px; height: 84px;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid var(--page-library-accent);
  border-radius: 10px;
  background: rgba(0, 212, 255, 0.05);
  color: var(--page-library-accent);
  font-family: var(--font-display);
  font-size: 38px; font-weight: 700; line-height: 1;
  opacity: 0;
  transform: rotate(-14deg) scale(0.9);
  transition: opacity var(--ease-out-soft), transform var(--ease-out-soft);
  pointer-events: none; user-select: none;
}
.paper-card:hover .pc-seal {
  opacity: 0.55;
  transform: rotate(-14deg) scale(1);
}

/* ── 骨架屏 ── */
.skeleton-grid :deep(.skeleton-block) {
  break-inside: avoid;
  margin-bottom: var(--space-md);
}

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
.pc-date { font-size: var(--text-xs); color: var(--text-muted); }
.empty-state { text-align: center; padding: var(--space-3xl); color: var(--text-muted); }
.empty-state p { margin-bottom: var(--space-md); }

/* ── 减弱动效 ── */
@media (prefers-reduced-motion: reduce) {
  .paper-card, .pc-seal { transition: none !important; }
}
</style>
