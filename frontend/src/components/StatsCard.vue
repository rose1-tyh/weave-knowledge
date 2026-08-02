<template>
  <div class="stats-card glass-panel">
    <div class="sc-icon" :style="{ color: accentColor }">{{ icon }}</div>
    <div class="sc-body">
      <span class="sc-value">{{ value }}</span>
      <span class="sc-label">{{ label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  icon: String,
  label: String,
  value: [Number, String],
  accent: { type: String, default: 'cyan' },
})
const colors = { cyan: '#00d4ff', vermilion: '#e8453c', amber: '#f59e0b', emerald: '#10b981', violet: '#8b5cf6' }
const accentColor = computed(() => colors[props.accent] || colors.cyan)
</script>

<style scoped>
.stats-card { display: flex; align-items: center; gap: var(--space-md); padding: var(--space-lg); }
.sc-icon { font-size: 24px; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.04); border-radius: var(--radius-md); }
.sc-value { font-family: var(--font-mono); font-size: var(--text-2xl); font-weight: 700; color: var(--text-primary); display: block; }
.sc-label { font-size: var(--text-sm); color: var(--text-muted); display: block; margin-top: 2px; }
</style>
