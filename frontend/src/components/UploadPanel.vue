<template>
  <div class="upload-panel" :class="{ 'is-dragover': isDragover, 'is-disabled': uploading }"
    @dragover.prevent="onDragOver" @dragleave.prevent="onDragLeave" @drop.prevent="onDrop" @click="triggerInput">
    <input ref="fileInput" type="file" accept=".pdf" style="display:none" @change="onFileChange" />
    <div class="up-icon">
      <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
        <rect x="10" y="8" width="36" height="40" rx="4" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M18 24h20M18 32h14M18 38h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="40" cy="20" r="8" fill="var(--vermilion, #e8453c)" stroke="var(--space-elevated, #111827)" stroke-width="2"/>
        <path d="M40 16v8M36 20h8" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
    </div>
    <p class="up-text" v-if="!uploading">
      <strong>拖拽论文 PDF 至此</strong><br />
      <span>或点击选择文件（最大 50MB）</span>
    </p>
    <p class="up-text" v-else>处理中...</p>
    <p class="up-error" v-if="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({ uploading: Boolean, error: String })
const emit = defineEmits(['upload'])
const fileInput = ref(null)
const isDragover = ref(false)

function triggerInput() {
  if (!props.uploading) fileInput.value?.click()
}
function onDragOver() { isDragover.value = true }
function onDragLeave() { isDragover.value = false }
function onDrop(e) { isDragover.value = false; const f = e.dataTransfer?.files?.[0]; if (f) emit('upload', f) }
function onFileChange(e) { const f = e.target.files?.[0]; if (f) emit('upload', f); if (fileInput.value) fileInput.value.value = '' }
</script>

<style scoped>
.upload-panel {
  border: 2px dashed var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-2xl);
  text-align: center;
  cursor: pointer;
  transition: all var(--ease-out);
  background: rgba(255,255,255,0.02);
}
.upload-panel:hover { border-color: var(--vermilion); background: var(--vermilion-bg); }
.upload-panel.is-dragover { border-color: var(--vermilion); background: var(--vermilion-bg); border-style: solid; box-shadow: var(--vermilion-glow); }
.upload-panel.is-disabled { cursor: not-allowed; opacity: 0.6; }
.up-icon { color: var(--text-muted); margin-bottom: var(--space-md); }
.is-dragover .up-icon { color: var(--vermilion); }
.up-text strong { color: var(--text-primary); font-size: var(--text-md); }
.up-text span { color: var(--text-muted); font-size: var(--text-sm); line-height: 2; }
.up-error { color: var(--vermilion); font-size: var(--text-sm); margin-top: var(--space-sm); }
</style>
