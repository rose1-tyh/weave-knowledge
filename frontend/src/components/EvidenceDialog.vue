<template>
  <el-dialog title="原文证据" v-model="visible" width="560px" append-to-body>
    <div v-if="loading" class="ev-loading">定位中…</div>
    <div v-else-if="!data?.found" class="ev-empty">{{ data?.reason || '原文不可用' }}</div>
    <template v-else>
      <div class="ev-meta">页码：第 {{ data.page }} 页</div>
      <p class="ev-context" v-html="highlighted"></p>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { evidenceContext } from '@/api'

const props = defineProps({ paperId: { type: String, required: true } })

const visible = ref(false)
const loading = ref(false)
const data = ref(null)

function open(text) {
  data.value = null
  visible.value = true
  loading.value = true
  evidenceContext(props.paperId, text || '')
    .then(res => { data.value = res })
    .catch(() => { data.value = { found: false, reason: '查询失败' } })
    .finally(() => { loading.value = false })
}

const highlighted = computed(() => {
  if (!data.value?.context) return ''
  const { context, start, end } = data.value
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // start/end 缺失或非整数（异常响应）→ 渲染转义后的完整上下文，避免 <mark> 切片错乱
  if (!Number.isInteger(start) || !Number.isInteger(end)) return esc(context)
  return `${esc(context.slice(0, start))}<mark class="ev-hit">${esc(context.slice(start, end))}</mark>${esc(context.slice(end))}`
})

defineExpose({ open })
</script>

<style scoped>
.ev-loading, .ev-empty { color: var(--text-muted); font-size: var(--text-sm); text-align: center; padding: var(--space-lg) 0; }
.ev-meta { font-size: var(--text-xs); color: var(--text-muted); margin-bottom: var(--space-sm); }
.ev-context { font-size: var(--text-sm); color: var(--text-secondary); line-height: 1.8; white-space: pre-wrap; }
.ev-hit { background: rgba(232, 69, 60, 0.18); color: #fff; padding: 0 2px; border-radius: 2px; }
</style>
