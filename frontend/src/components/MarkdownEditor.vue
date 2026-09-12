<template>
  <div class="md-editor" :class="{ 'preview-only': !editable }">
    <!-- 工具栏（仅编辑态） -->
    <div v-if="editable" class="mde-toolbar">
      <button v-for="t in tools" :key="t.title" class="mde-tool" type="button"
        :title="t.title" @click="t.run()">{{ t.label }}</button>
      <button class="mde-tool mde-mode" type="button" :title="preview ? '回到编辑' : '预览'"
        @click="preview = !preview">
        {{ preview ? '编辑' : '预览' }}
      </button>
    </div>

    <!-- 编辑 + 实时预览（双栏） -->
    <div v-if="editable" class="mde-panes" :class="{ single: !preview }">
      <textarea
        ref="textareaRef"
        class="mde-input"
        :value="modelValue"
        :placeholder="placeholder"
        :rows="rows"
        @input="onInput"
        @keydown="onKeydown"
      ></textarea>
      <div v-if="preview" class="mde-preview md-body" v-html="rendered"></div>
    </div>

    <!-- 只读渲染 -->
    <div v-else class="mde-preview md-body" v-html="rendered"></div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '支持 Markdown：**加粗**、列表、`代码`、[链接](url)…' },
  rows: { type: Number, default: 6 },
  editable: { type: Boolean, default: true },
  preview: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue'])

const textareaRef = ref(null)
const showPreview = ref(props.preview)

const rendered = computed(() => renderMarkdown(props.modelValue))

function onInput(e) {
  emit('update:modelValue', e.target.value)
}

// 常用语法一键插入（保持选区）
function wrapSel(before, after = before) {
  const el = textareaRef.value
  if (!el) return
  const { selectionStart: s, selectionEnd: e, value } = el
  const inner = value.slice(s, e) || '文本'
  const next = value.slice(0, s) + before + inner + after + value.slice(e)
  emit('update:modelValue', next)
  requestAnimationFrame(() => {
    el.focus()
    el.setSelectionRange(s + before.length, s + before.length + inner.length)
  })
}
function linePrefix(prefix) {
  const el = textareaRef.value
  if (!el) return
  const { selectionStart: s, selectionEnd: e, value } = el
  const ls = value.lastIndexOf('\n', s - 1) + 1
  const next = value.slice(0, ls) + prefix + value.slice(ls)
  emit('update:modelValue', next)
  requestAnimationFrame(() => {
    el.focus()
    el.setSelectionRange(s + prefix.length, e + prefix.length)
  })
}

const tools = [
  { title: '加粗', label: 'B', run: () => wrapSel('**') },
  { title: '斜体', label: 'I', run: () => wrapSel('*') },
  { title: '行内代码', label: '</>', run: () => wrapSel('`') },
  { title: '标题', label: 'H', run: () => linePrefix('## ') },
  { title: '无序列表', label: '•', run: () => linePrefix('- ') },
  { title: '链接', label: '↗', run: () => wrapSel('[', '](https://)') },
]

// 快捷键：Ctrl+B / Ctrl+I
function onKeydown(e) {
  if (!(e.ctrlKey || e.metaKey)) return
  const k = e.key.toLowerCase()
  if (k === 'b') { e.preventDefault(); wrapSel('**') }
  if (k === 'i') { e.preventDefault(); wrapSel('*') }
}
</script>

<style scoped>
.md-editor { display: flex; flex-direction: column; gap: 6px; width: 100%; }

.mde-toolbar {
  display: flex;
  gap: 2px;
  padding: 2px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--space-surface);
  width: fit-content;
}
.mde-tool {
  min-width: 26px;
  height: 24px;
  padding: 0 6px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: all var(--ease-out);
}
.mde-tool:hover { color: var(--vermilion); background: var(--hover-tint); }
.mde-mode { margin-left: auto; font-family: var(--font-body); }

.mde-panes { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-sm); }
.mde-panes.single { grid-template-columns: 1fr; }

.mde-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--space-surface);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  line-height: 1.6;
  resize: vertical;
  outline: none;
  transition: border-color var(--ease-out);
}
.mde-input:focus { border-color: var(--vermilion); }

.mde-preview {
  padding: 8px 10px;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  line-height: 1.7;
  color: var(--text-primary);
  overflow-wrap: break-word;
  max-height: 260px;
  overflow-y: auto;
}
</style>

<style>
/* Markdown 渲染体（非 scoped：v-html 内容无法命中 scoped 规则） */
.md-body p { margin: 0 0 0.5em; }
.md-body p:last-child { margin-bottom: 0; }
.md-body h1, .md-body h2, .md-body h3, .md-body h4 {
  margin: 0.6em 0 0.3em;
  font-family: var(--font-display);
  color: var(--text-primary);
}
.md-body ul, .md-body ol { margin: 0.3em 0 0.5em; padding-left: 1.4em; }
.md-body code {
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  background: var(--hover-tint);
  font-family: var(--font-mono);
  font-size: 0.92em;
  color: var(--cyan);
}
.md-body pre {
  margin: 0.4em 0;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--hover-tint);
  overflow-x: auto;
}
.md-body pre code { background: transparent; padding: 0; }
.md-body a { color: var(--cyan); text-decoration: none; }
.md-body a:hover { text-decoration: underline; }
.md-body blockquote {
  margin: 0.4em 0;
  padding: 2px 10px;
  border-left: 2px solid var(--vermilion);
  color: var(--text-secondary);
  background: var(--space-surface);
}
.md-body hr { border: none; border-top: 1px dashed var(--border-default); margin: 0.6em 0; }
</style>
