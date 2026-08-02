<template>
  <div class="matrix-view">
    <h4 class="mv-title">关系矩阵</h4>
    <div class="mv-scroll" v-if="matrix.labels.length">
      <table class="mv-table">
        <thead>
          <tr>
            <th></th>
            <th v-for="l in matrix.labels" :key="l" :title="l">{{ l.length > 4 ? l.slice(0,4)+'…' : l }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in matrix.grid" :key="matrix.labels[ri]">
            <th :title="matrix.labels[ri]">{{ matrix.labels[ri].length > 4 ? matrix.labels[ri].slice(0,4)+'…' : matrix.labels[ri] }}</th>
            <td v-for="(cell, ci) in row" :key="ci"
              :style="{ background: cellColor(cell) }"
              :title="cell ? cell.type : ''"
              @click="cell && $emit('select-relation', cell)"
            ></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="mv-empty">暂无关系数据</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  concepts: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] },
})
defineEmits(['select-relation'])

const relColors = { supports: '#10b981', contradicts: '#e8453c', extends: '#f59e0b', cites: '#6b7280', uses: '#00d4ff' }

const matrix = computed(() => {
  const names = props.concepts.map(c => c.name)
  const n = names.length
  const grid = Array.from({ length: n }, () => Array(n).fill(null))
  for (const l of props.links) {
    const si = names.indexOf(props.concepts.find(c => c.id === l.source)?.name)
    const ti = names.indexOf(props.concepts.find(c => c.id === l.target)?.name)
    if (si >= 0 && ti >= 0) grid[si][ti] = l
  }
  return { labels: names, grid }
})

function cellColor(cell) {
  if (!cell) return 'transparent'
  return (relColors[cell.type] || '#6b7280') + '44'
}
</script>

<style scoped>
.matrix-view { padding: var(--space-lg); height: 100%; display: flex; flex-direction: column; }
.mv-title { font-family: var(--font-display); font-size: var(--text-md); color: var(--text-primary); margin-bottom: var(--space-md); flex-shrink: 0; }
.mv-scroll { flex: 1; overflow: auto; }
.mv-table { border-collapse: collapse; }
.mv-table th, .mv-table td {
  width: 40px; height: 28px;
  text-align: center;
  font-size: var(--text-xs);
  border: 1px solid var(--border-subtle);
}
.mv-table th { color: var(--text-muted); font-weight: 400; white-space: nowrap; }
.mv-table td { cursor: pointer; transition: background var(--ease-out); }
.mv-table td:hover { outline: 1px solid var(--vermilion); }
.mv-empty { text-align: center; padding: var(--space-xl); color: var(--text-muted); }
</style>
