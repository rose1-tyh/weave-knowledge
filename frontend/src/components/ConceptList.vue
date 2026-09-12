<template>
  <div class="concept-list">
    <div class="cl-header">
      <h4>核心概念</h4>
      <span class="cl-count">{{ concepts.length }}</span>
      <button v-if="editing" class="cl-add-btn" @click="$emit('add')">+ 新增</button>
    </div>
    <div class="cl-search">
      <input v-model="filter" placeholder="搜索概念..." class="cl-search-input" />
    </div>
    <div class="cl-groups">
      <div v-for="group in groupedConcepts" :key="group.type" class="cl-group">
        <div class="cl-group-label" :style="{ color: group.color }">{{ group.label }}</div>
        <div
          v-for="c in group.items" :key="c.id"
          class="cl-item"
          :class="{ selected: c.id === selectedId }"
          @click="$emit('select', c.id)"
        >
          <span class="cl-dot" :style="{ background: c.color }"></span>
          <span class="cl-name">{{ c.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { typeMeta } from '@/design/tokens'

const props = defineProps({
  concepts: { type: Array, default: () => [] },
  selectedId: { type: String, default: null },
  editing: Boolean,
})
defineEmits(['select', 'add'])

const filter = ref('')

const groupedConcepts = computed(() => {
  const q = filter.value.toLowerCase()
  const filtered = q ? props.concepts.filter(c => c.name.toLowerCase().includes(q)) : props.concepts
  const groups = {}
  for (const c of filtered) {
    const t = c.type || 'finding'
    if (!groups[t]) groups[t] = []
    groups[t].push(c)
  }
  return Object.entries(groups).map(([type, items]) => ({
    type,
    label: typeMeta(type)?.label,
    color: typeMeta(type)?.color,
    items,
  }))
})
</script>

<style scoped>
.concept-list { padding: var(--space-md); }
.cl-header { display: flex; align-items: center; gap: var(--space-sm); margin-bottom: var(--space-md); }
.cl-header h4 { font-family: var(--font-display); font-size: var(--text-md); color: var(--text-primary); flex: 1; }
.cl-count { font-size: var(--text-xs); color: var(--text-muted); background: var(--hover-tint); padding: 1px 8px; border-radius: 10px; }
.cl-add-btn { border: 1px solid var(--vermilion); background: var(--vermilion-bg); color: var(--vermilion); font-size: var(--text-xs); padding: 2px 8px; border-radius: var(--radius-sm); cursor: pointer; font-family: inherit; }
.cl-add-btn:hover { background: var(--vermilion); color: #fff; }
.cl-search { margin-bottom: var(--space-md); }
.cl-search-input { width: 100%; padding: 6px 10px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); background: var(--space-surface); color: var(--text-primary); font-size: var(--text-sm); font-family: inherit; outline: none; }
.cl-search-input:focus { border-color: var(--vermilion); }
.cl-search-input::placeholder { color: var(--text-disabled); }
.cl-group { margin-bottom: var(--space-md); }
.cl-group-label { font-size: var(--text-xs); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: var(--space-xs); }
.cl-item { display: flex; align-items: center; gap: var(--space-sm); padding: 6px 8px; border-radius: var(--radius-sm); cursor: pointer; font-size: var(--text-sm); color: var(--text-secondary); transition: all var(--ease-out); }
.cl-item:hover { background: var(--space-surface); color: var(--text-primary); }
.cl-item.selected { background: var(--vermilion-bg); color: var(--vermilion); }
.cl-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.cl-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
