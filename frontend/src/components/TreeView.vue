<template>
  <div class="tree-view">
    <h4 class="tv-title">知识层级</h4>
    <div class="tv-tree" v-if="tree.length">
      <div v-for="group in tree" :key="group.label" class="tv-group">
        <div class="tv-group-header" @click="group.expanded = !group.expanded">
          <span class="tv-arrow" :class="{ open: group.expanded }">▸</span>
          <span class="tv-group-dot" :style="{ background: group.color }"></span>
          <span class="tv-group-label">{{ group.label }}</span>
          <span class="tv-count">{{ group.items.length }}</span>
        </div>
        <div class="tv-items" v-show="group.expanded">
          <div v-for="c in group.items" :key="c.id" class="tv-item"
            :class="{ selected: c.id === selectedId }"
            @click="$emit('select', c.id)">
            <span class="tv-name">{{ c.name }}</span>
            <span class="tv-def">{{ c.definition }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="tv-empty">暂无知觉数据</div>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { typeMeta } from '@/design/tokens'

const props = defineProps({
  concepts: { type: Array, default: () => [] },
  selectedId: { type: String, default: null },
})
defineEmits(['select'])

const tree = computed(() => {
  const groups = {}
  for (const c of props.concepts) {
    const t = c.type || 'finding'
    if (!groups[t]) groups[t] = []
    groups[t].push(c)
  }
  return Object.entries(groups).map(([type, items]) => ({
    label: typeMeta(type)?.label,
    color: typeMeta(type)?.color,
    items,
    expanded: true,
  }))
})
</script>

<style scoped>
.tree-view { padding: var(--space-lg); }
.tv-title { font-family: var(--font-display); font-size: var(--text-md); color: var(--text-primary); margin-bottom: var(--space-md); }
.tv-group { margin-bottom: var(--space-md); }
.tv-group-header { display: flex; align-items: center; gap: var(--space-sm); cursor: pointer; padding: 4px 0; user-select: none; }
.tv-arrow { font-size: 10px; color: var(--text-muted); transition: transform var(--ease-out); width: 12px; }
.tv-arrow.open { transform: rotate(90deg); }
.tv-group-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.tv-group-label { font-size: var(--text-xs); font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; }
.tv-count { font-size: var(--text-xs); color: var(--text-muted); margin-left: auto; }
.tv-item { padding: 6px 8px 6px 32px; cursor: pointer; border-radius: var(--radius-sm); font-size: var(--text-sm); color: var(--text-secondary); }
.tv-item:hover { background: var(--space-surface); color: var(--text-primary); }
.tv-item.selected { background: var(--vermilion-bg); color: var(--vermilion); }
.tv-name { display: block; }
.tv-def { display: block; font-size: var(--text-xs); color: var(--text-muted); margin-top: 2px; }
.tv-empty { text-align: center; padding: var(--space-xl); color: var(--text-muted); }
</style>
