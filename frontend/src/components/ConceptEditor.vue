<template>
  <div class="concept-editor">
    <div class="ce-header">
      <span class="ce-type-badge" :style="{ background: concept ? (typeMeta[concept.type]?.color || '#6b7280') : '#6b7280' }">
        {{ concept ? (typeMeta[concept.type]?.label || '概念') : '新增概念' }}
      </span>
      <button class="ce-close" @click="$emit('close')">&times;</button>
    </div>

    <template v-if="!editing && concept">
      <!-- 只读模式 -->
      <h3 class="ce-name">{{ concept.name }}</h3>
      <p class="ce-def">{{ concept.definition }}</p>
      <div class="ce-meta">
        <span>原文页码：第 {{ concept.page }} 页</span>
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
        <textarea v-model="form.definition" class="ce-textarea" rows="3" placeholder="一句话定义"></textarea>
        <label>类型</label>
        <select v-model="form.type" class="ce-input">
          <option v-for="(m, k) in typeMeta" :key="k" :value="k">{{ m.label }}</option>
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

const props = defineProps({
  concept: { type: Object, default: null },
  editing: Boolean,
})
defineEmits(['save', 'delete', 'close'])

const typeMeta = {
  method: { label: '研究方法', color: '#e8453c' },
  theory: { label: '理论基础', color: '#8b5cf6' },
  dataset: { label: '数据集', color: '#10b981' },
  finding: { label: '研究发现', color: '#f59e0b' },
  tool: { label: '工具/系统', color: '#00d4ff' },
}

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
.ce-close:hover { background: rgba(255,255,255,0.06); color: var(--text-primary); }
.ce-name { font-family: var(--font-display); font-size: var(--text-xl); color: var(--text-primary); margin-bottom: var(--space-md); }
.ce-def { font-size: var(--text-base); color: var(--text-secondary); line-height: 1.7; margin-bottom: var(--space-lg); }
.ce-meta span { font-size: var(--text-sm); color: var(--text-muted); }
.ce-form { display: flex; flex-direction: column; gap: 6px; }
.ce-form label { font-size: var(--text-xs); color: var(--text-muted); margin-top: var(--space-sm); }
.ce-input, .ce-textarea {
  width: 100%; padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.04);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  outline: none;
  resize: vertical;
}
.ce-input:focus, .ce-textarea:focus { border-color: var(--vermilion); }
.ce-actions { display: flex; gap: var(--space-sm); margin-top: var(--space-lg); }
.ce-empty { color: var(--text-muted); font-size: var(--text-sm); text-align: center; padding: var(--space-xl) 0; }
</style>
