<template>
  <div class="graph-toolbar glass-panel">
    <button class="tb-btn" title="放大" @click="$emit('zoom-in')">+</button>
    <button class="tb-btn" title="缩小" @click="$emit('zoom-out')">−</button>
    <button class="tb-btn" title="重置视图" @click="$emit('reset')">⟲</button>
    <span class="tb-divider"></span>
    <button class="tb-btn" :class="{ active: editing }" title="编辑模式" @click="$emit('toggle-edit')">✎</button>
    <button class="tb-btn" title="撤销" :disabled="!canUndo" @click="$emit('undo')">↩</button>
    <button class="tb-btn" title="重做" :disabled="!canRedo" @click="$emit('redo')">↪</button>
    <span class="tb-divider"></span>
    <button class="tb-btn" title="导出 PNG" @click="$emit('export-png')">🖼</button>
    <button class="tb-btn" title="导出 JSON" @click="$emit('export-json')">JSON</button>
    <button class="tb-btn" title="导出 Markdown" @click="$emit('export-md')">MD</button>
  </div>
</template>

<script setup>
defineProps({
  editing: Boolean,
  canUndo: Boolean,
  canRedo: Boolean,
})
defineEmits(['zoom-in', 'zoom-out', 'reset', 'toggle-edit', 'undo', 'redo', 'export-png', 'export-json', 'export-md'])
</script>

<style scoped>
.graph-toolbar {
  position: absolute;
  top: var(--space-md);
  right: var(--space-md);
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 8px;
  z-index: 10;
}
.tb-btn {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
  transition: all var(--ease-out);
}
.tb-btn:hover { background: rgba(255,255,255,0.08); color: var(--text-primary); }
.tb-btn.active { color: var(--vermilion); background: var(--vermilion-bg); }
.tb-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.tb-divider {
  width: 1px; height: 16px;
  background: var(--border-subtle);
  margin: 0 4px;
}
</style>
