<template>
  <div class="concept-card">
    <!-- 空态 -->
    <div v-if="!concept" class="card-empty">
      <div class="empty-icon">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
          <circle cx="20" cy="14" r="6" stroke="currentColor" stroke-width="1.5"/>
          <path d="M8 34c0-6.6 5.4-12 12-12s12 5.4 12 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      <p class="empty-title">点击图谱中的节点</p>
      <p class="empty-desc">查看概念的详细定义与原文依据</p>
    </div>

    <!-- 详情 -->
    <template v-else>
      <div class="card-header">
        <div class="concept-badge" :style="{ background: typeColor }">
          {{ typeLabel }}
        </div>
        <button class="card-close" @click="$emit('close')">&times;</button>
      </div>
      <h3 class="concept-name">{{ concept.name }}</h3>
      <p class="concept-definition">{{ concept.definition }}</p>

      <div class="card-meta">
        <div class="meta-item">
          <span class="meta-label">原文页码</span>
          <span class="meta-value">第 {{ concept.page }} 页</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  concept: { type: Object, default: null },
  paperTitle: { type: String, default: '' },
})

defineEmits(['close'])

const typeMap = {
  method: { label: '研究方法', color: '#b5343a' },
  theory: { label: '理论基础', color: '#1c1c28' },
  dataset: { label: '数据集', color: '#3a7d6e' },
  finding: { label: '研究发现', color: '#d4893a' },
  tool: { label: '工具/系统', color: '#6b7280' },
}

const typeLabel = computed(() => typeMap[props.concept?.type]?.label || '概念')
const typeColor = computed(() => typeMap[props.concept?.type]?.color || '#6b7280')
</script>

<style scoped>
.concept-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 空态 */
.card-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-2xl);
  text-align: center;
}
.empty-icon {
  color: var(--border);
  margin-bottom: var(--space-md);
}
.empty-title {
  font-family: var(--font-display);
  font-size: var(--text-md);
  color: var(--text-secondary);
  margin-bottom: var(--space-xs);
}
.empty-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  line-height: 1.6;
}

/* 有内容 */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg) var(--space-lg) 0;
}
.concept-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  color: #fff;
  font-size: var(--text-xs);
  font-weight: 500;
}
.card-close {
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  font-size: 18px;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-close:hover {
  background: var(--paper-warm);
  color: var(--text-primary);
}

.concept-name {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  color: var(--ink);
  padding: var(--space-md) var(--space-lg) 0;
}
.concept-definition {
  font-size: var(--text-base);
  color: var(--text-secondary);
  line-height: 1.7;
  padding: var(--space-md) var(--space-lg);
}

.card-meta {
  margin: 0 var(--space-lg);
  padding: var(--space-md) 0;
  border-top: 1px solid var(--border-light);
}
.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.meta-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.meta-value {
  font-size: var(--text-sm);
  color: var(--text-primary);
}
</style>
