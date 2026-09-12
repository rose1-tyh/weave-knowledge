<template>
  <div class="concept-editor">
    <div class="ce-header">
      <span class="ce-type-badge" :style="{ background: concept ? (TYPE_META[concept.type]?.color || '#6b7280') : '#6b7280' }">
        {{ concept ? (TYPE_META[concept.type]?.label || '概念') : '新增概念' }}
      </span>
      <button class="ce-close" @click="$emit('close')">&times;</button>
    </div>

    <template v-if="!editing && concept">
      <!-- 只读模式 -->
      <h3 class="ce-name">{{ concept.name }}</h3>
      <div class="ce-status-row">
        <span class="ce-status-badge" :class="concept.status">{{ statusLabel(concept.status) }}</span>
        <span class="ce-conf">置信度 {{ confPercent(concept.confidence) }}</span>
      </div>
      <p v-if="isLowConfidence(concept.confidence)" class="ce-lowhint">低置信，建议人工确认</p>
      <MarkdownEditor
        v-if="concept.definition"
        :model-value="concept.definition"
        :editable="false"
      />
      <p v-else class="ce-def ce-def-empty">暂无定义</p>
      <div class="ce-meta">
        <span>原文页码：第 {{ concept.page }} 页</span>
      </div>
      <div v-if="concept.evidence" class="ce-evidence">
        <span class="ce-evidence-label">原文片段</span>
        <p class="ce-evidence-text" @click="$emit('evidence')">{{ concept.evidence }}</p>
      </div>
      <div v-if="concept.status !== 'confirmed'" class="ce-confirm-actions">
        <el-button size="small" type="primary" data-test="confirm" @click="$emit('confirm')">确认</el-button>
        <el-button size="small" data-test="reject" @click="$emit('reject')">驳回</el-button>
      </div>
    </template>

    <template v-else-if="!editing">
      <p class="ce-empty">未选择概念</p>
    </template>

    <template v-else>
      <!-- 编辑/新增模式 -->
      <div class="ce-form">
        <label>名称</label>
        <input v-model="form.name" class="ce-input" placeholder="概念名称（2-8 字）" />
        <label>定义</label>
        <MarkdownEditor v-model="form.definition" :rows="5" />
        <label>类型</label>
        <select v-model="form.type" class="ce-input">
          <option v-for="(m, k) in TYPE_META" :key="k" :value="k">{{ m.label }}</option>
        </select>
        <label>页码</label>
        <input v-model.number="form.page" type="number" class="ce-input" min="1" />
        <div class="ce-actions">
          <el-button size="small" type="primary" @click="$emit('save', { ...form, slug: concept?.id })">保存</el-button>
          <el-button v-if="concept" size="small" type="danger" @click="$emit('delete', concept?.id)">删除</el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { isLowConfidence, statusLabel, confPercent } from '@/utils/confidence'
import MarkdownEditor from '@/components/MarkdownEditor.vue'
import { TYPE_META } from '@/design/tokens'

const props = defineProps({
  concept: { type: Object, default: null },
  editing: Boolean,
})
defineEmits(['save', 'delete', 'close', 'confirm', 'reject', 'evidence'])

const form = ref({ name: '', definition: '', type: 'finding', page: 1 })

watch(() => props.concept, (c) => {
  if (c) form.value = { name: c.name, definition: c.definition, type: c.type, page: c.page }
}, { immediate: true })
</script>

<style scoped>
.concept-editor { padding: var(--space-lg); }
.ce-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-md); }
.ce-type-badge { padding: 2px 10px; border-radius: 12px; color: #fff; font-size: var(--text-xs); font-weight: 500; }
.ce-close { width: 28px; height: 28px; border: none; background: none; color: var(--text-muted); font-size: 20px; cursor: pointer; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; }
.ce-close:hover { background: var(--hover-tint); color: var(--text-primary); }
.ce-name { font-family: var(--font-display); font-size: var(--text-xl); color: var(--text-primary); margin-bottom: var(--space-md); }
.ce-def { font-size: var(--text-base); color: var(--text-secondary); line-height: 1.7; margin-bottom: var(--space-lg); }
.ce-meta span { font-size: var(--text-sm); color: var(--text-muted); }
.ce-form { display: flex; flex-direction: column; gap: 6px; }
.ce-form label { font-size: var(--text-xs); color: var(--text-muted); margin-top: var(--space-sm); }
.ce-def-empty { color: var(--text-muted); font-style: italic; }
.ce-input, .ce-textarea {
  width: 100%; padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--space-surface);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  outline: none;
  resize: vertical;
}
.ce-input:focus, .ce-textarea:focus { border-color: var(--vermilion); }
.ce-actions { display: flex; gap: var(--space-sm); margin-top: var(--space-lg); }
.ce-empty { color: var(--text-muted); font-size: var(--text-sm); text-align: center; padding: var(--space-xl) 0; }
.ce-status-row { display: flex; align-items: center; gap: var(--space-sm); margin-bottom: var(--space-sm); }
.ce-status-badge { padding: 2px 8px; border-radius: 12px; font-size: var(--text-xs); font-weight: 600; }
.ce-status-badge.pending { color: #f59e0b; border: 1px solid #f59e0b; }
.ce-status-badge.confirmed { color: #10b981; border: 1px solid #10b981; }
.ce-status-badge.rejected { color: var(--text-muted); border: 1px solid var(--border-strong); }
.ce-conf { font-size: var(--text-xs); color: var(--text-muted); }
.ce-lowhint { font-size: var(--text-xs); color: #f59e0b; margin-bottom: var(--space-sm); }
.ce-evidence { margin-bottom: var(--space-lg); }
.ce-evidence-label { font-size: var(--text-xs); color: var(--text-muted); }
.ce-evidence-text { font-size: var(--text-sm); color: var(--text-secondary); font-style: italic; border-left: 2px solid var(--vermilion); padding-left: var(--space-sm); margin-top: 4px; line-height: 1.6; cursor: pointer; }
.ce-confirm-actions { display: flex; gap: var(--space-sm); margin-top: var(--space-sm); }
</style>
