<template>
  <div class="view-switcher glass-panel">
    <button v-for="v in views" :key="v.key" class="vs-btn" :class="{ active: active === v.key }"
      :title="v.label" @click="$emit('switch', v.key)">
      {{ v.icon }}
    </button>
  </div>
</template>

<script setup>
defineProps({ active: { type: String, default: 'graph' } })
defineEmits(['switch'])
const views = [
  { key: 'graph', label: '力导向图', icon: '◎' },
  { key: 'tree', label: '层级树', icon: '▦' },
  { key: 'matrix', label: '关系矩阵', icon: '⊞' },
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
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: 16px;
  cursor: pointer;
  transition: all var(--ease-out);
}
.vs-btn:hover { color: var(--text-primary); background: rgba(255,255,255,0.06); }
.vs-btn.active { color: var(--cyan); background: var(--cyan-bg); }
</style>
