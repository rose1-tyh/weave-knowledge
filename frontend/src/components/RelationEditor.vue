<template>
  <div class="relation-editor" v-if="link">
    <div class="re-header">
      <span class="re-type-badge" :style="{ background: relColors[link.type] || '#6b7280' }">
        {{ relLabels[link.type] || link.type }}
      </span>
      <button class="re-close" @click="$emit('close')">&times;</button>
    </div>
    <div class="re-chain">
      <span class="re-node-label">{{ sourceName }}</span>
      <span class="re-arrow">→</span>
      <span class="re-node-label">{{ targetName }}</span>
    </div>
    <p class="re-evidence" v-if="link.evidence">"{{ link.evidence }}"</p>
    <div class="re-status-row">
      <span class="re-status-badge" :class="link.status">{{ statusLabel(link.status) }}</span>
      <span class="re-conf">置信度 {{ confPercent(link.confidence) }}</span>
    </div>
    <p v-if="isLowConfidence(link.confidence)" class="re-lowhint">低置信，建议人工确认</p>
    <div v-if="link.status !== 'confirmed'" class="re-confirm-actions">
      <el-button size="small" type="primary" data-test="confirm" @click="$emit('confirm')">确认</el-button>
      <el-button size="small" data-test="reject" @click="$emit('reject')">驳回</el-button>
    </div>

    <div v-if="editing" class="re-form">
      <label>关系类型</label>
      <select v-model="form.type" class="re-select">
        <option v-for="(label, key) in relLabels" :key="key" :value="key">{{ label }}</option>
      </select>
      <label>原文依据</label>
      <textarea v-model="form.evidence" class="re-textarea" rows="2"></textarea>
      <div class="re-actions">
        <el-button size="small" type="primary" @click="$emit('save', { ...form, id: linkIndex, relId: props.link?.relId })">保存</el-button>
        <el-button size="small" type="danger" @click="$emit('delete', { id: linkIndex, relId: props.link?.relId })">删除</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { isLowConfidence, statusLabel, confPercent } from '@/utils/confidence'

const props = defineProps({
  link: { type: Object, default: null },
  linkIndex: { type: Number, default: null },
  nodes: { type: Array, default: () => [] },
  editing: Boolean,
})
defineEmits(['save', 'delete', 'close', 'confirm', 'reject'])

const relLabels = { supports: '支撑', contradicts: '矛盾', extends: '扩展', cites: '引用', uses: '使用' }
const relColors = { supports: '#10b981', contradicts: '#e8453c', extends: '#f59e0b', cites: '#6b7280', uses: '#00d4ff' }

const sourceName = computed(() => {
  const n = props.nodes?.find(n => n.id === props.link?.source)
  return n?.name || props.link?.source || '?'
})
const targetName = computed(() => {
  const n = props.nodes?.find(n => n.id === props.link?.target)
  return n?.name || props.link?.target || '?'
})
const linkIndex = computed(() => props.linkIndex ?? null)

const form = ref({ type: 'cites', evidence: '' })
watch(() => props.link, (l) => {
  if (l) form.value = { type: l.type, evidence: l.evidence || '' }
}, { immediate: true })
</script>

<style scoped>
.relation-editor { padding: var(--space-lg); }
.re-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-md); }
.re-type-badge { padding: 2px 10px; border-radius: 12px; color: #fff; font-size: var(--text-xs); font-weight: 500; }
.re-close { width: 28px; height: 28px; border: none; background: none; color: var(--text-muted); font-size: 20px; cursor: pointer; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; }
.re-chain { display: flex; align-items: center; gap: var(--space-sm); margin-bottom: var(--space-md); font-size: var(--text-md); }
.re-node-label { color: var(--text-primary); font-weight: 600; }
.re-arrow { color: var(--text-muted); }
.re-evidence { font-size: var(--text-sm); color: var(--text-secondary); font-style: italic; line-height: 1.6; margin-bottom: var(--space-lg); }
.re-form { display: flex; flex-direction: column; gap: 6px; }
.re-form label { font-size: var(--text-xs); color: var(--text-muted); margin-top: var(--space-sm); }
.re-select, .re-textarea {
  width: 100%; padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.04);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  outline: none;
}
.re-select:focus, .re-textarea:focus { border-color: var(--vermilion); }
.re-actions { display: flex; gap: var(--space-sm); margin-top: var(--space-lg); }
.re-status-row { display: flex; align-items: center; gap: var(--space-sm); margin-bottom: var(--space-sm); }
.re-status-badge { padding: 2px 8px; border-radius: 12px; font-size: var(--text-xs); font-weight: 600; }
.re-status-badge.pending { color: #f59e0b; border: 1px solid #f59e0b; }
.re-status-badge.confirmed { color: #10b981; border: 1px solid #10b981; }
.re-status-badge.rejected { color: var(--text-muted); border: 1px solid var(--border-strong); }
.re-conf { font-size: var(--text-xs); color: var(--text-muted); }
.re-lowhint { font-size: var(--text-xs); color: #f59e0b; margin-bottom: var(--space-sm); }
.re-confirm-actions { display: flex; gap: var(--space-sm); margin-top: var(--space-sm); }
</style>
