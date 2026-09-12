<template>
  <div class="global-search">
    <div class="gs-input-wrap">
      <input ref="inputEl" v-model="query" placeholder="搜索所有概念..." class="gs-input" @keyup.enter="doSearch" />
    </div>
    <div class="gs-results" v-if="results.length">
      <div v-for="r in results" :key="r.id" class="gs-item" @click="$emit('select', r)">
        <span class="gs-dot" :style="{ background: r.color || 'var(--text-muted)' }"></span>
        <div class="gs-info">
          <span class="gs-name">{{ r.name }}</span>
          <span v-if="r.definition" class="gs-def">{{ r.definition }}</span>
          <span class="gs-paper">{{ r.paperTitle }}</span>
        </div>
      </div>
    </div>
    <div class="gs-empty" v-else-if="query && searched">
      <p>未找到匹配概念</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  results: { type: Array, default: () => [] },
  /** 挂载后自动聚焦输入框（用于 ⌘K 全局搜索面板） */
  autofocus: { type: Boolean, default: false },
})
const emit = defineEmits(['search', 'select'])
const query = ref('')
const searched = ref(false)
const inputEl = ref(null)

function doSearch() {
  searched.value = true
  emit('search', query.value)
}

function focus() {
  inputEl.value?.focus()
}

onMounted(() => {
  if (props.autofocus) focus()
})

defineExpose({ focus, clear: () => { query.value = ''; searched.value = false } })
</script>

<style scoped>
.global-search { padding: var(--space-lg); }
.gs-input-wrap { margin-bottom: var(--space-md); }
.gs-input {
  width: 100%; padding: 8px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--space-surface);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  outline: none;
}
.gs-input:focus { border-color: var(--cyan); }
.gs-input::placeholder { color: var(--text-disabled); }
.gs-item {
  display: flex; align-items: flex-start; gap: var(--space-sm);
  padding: var(--space-sm) 0;
  cursor: pointer;
  border-bottom: 1px solid var(--border-subtle);
}
.gs-item:hover .gs-name { color: var(--cyan); }
.gs-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }
.gs-info { flex: 1; min-width: 0; }
.gs-name { font-size: var(--text-sm); color: var(--text-primary); display: block; }
.gs-def {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: var(--text-xs); color: var(--text-secondary); line-height: 1.6;
  margin-top: 2px;
}
.gs-paper { font-size: var(--text-xs); color: var(--text-muted); display: block; margin-top: 2px; }
.gs-empty { text-align: center; padding: var(--space-lg); color: var(--text-muted); font-size: var(--text-sm); }
</style>
