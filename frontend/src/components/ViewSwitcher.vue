<template>
  <div class="view-switcher glass-panel" role="tablist" aria-label="视图切换">
    <button v-for="v in views" :key="v.key" class="vs-btn" :class="{ active: active === v.key }"
      :title="v.label" role="tab" :aria-selected="active === v.key" @click="$emit('switch', v.key)">
      <el-icon class="vs-icon" aria-hidden="true"><component :is="v.icon" /></el-icon>
      <span class="vs-label">{{ v.label }}</span>
    </button>
  </div>
</template>

<script setup>
import { Share, Grid, Operation } from '@element-plus/icons-vue'

defineProps({ active: { type: String, default: 'graph' } })
defineEmits(['switch'])
const views = [
  { key: 'graph', label: '图谱', icon: Share },
  { key: 'tree', label: '层级', icon: Grid },
  { key: 'matrix', label: '矩阵', icon: Operation },
]
</script>

<style scoped>
.view-switcher {
  position: absolute;
  bottom: var(--space-md);
  right: var(--space-md);
  display: flex;
  gap: 2px;
  padding: 4px;
  z-index: 10;
}
.vs-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px;
  border: none; border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-family: inherit;
  cursor: pointer;
  transition: all var(--ease-out);
  user-select: none;
}
.vs-btn:hover { color: var(--text-primary); background: var(--hover-tint); }
.vs-btn.active { color: var(--cyan); background: var(--cyan-bg); }
.vs-icon { font-size: 14px; line-height: 1; }
</style>
