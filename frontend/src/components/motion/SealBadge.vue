<template>
  <span class="seal-badge" :class="status">
    <span class="seal-inner">{{ text }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  text: { type: String, default: '' },
  status: { type: String, default: 'done' }, // done|pending|processing|failed
})
const text = computed(() => {
  if (props.text) return props.text
  return { done: '已提取', pending: '待提取', processing: '织网中', failed: '失败' }[props.status] || '未知'
})
</script>

<style scoped>
.seal-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  border: 1.5px solid currentColor;
  background: transparent;
  transform: rotate(-2deg);
}
.seal-inner { border-top: 1px solid currentColor; border-bottom: 1px solid currentColor; padding: 1px 4px; }
.done { color: #10b981; }
.pending { color: #6b7280; }
.processing { color: #c9a227; animation: seal-pulse 1.6s ease-in-out infinite; }
.failed { color: #e8453c; }
@keyframes seal-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
</style>
