<template>
  <div class="skeleton-block" :style="styleObj"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  width: { type: String, default: '100%' },
  height: { type: String, default: '16px' },
  radius: { type: String, default: '8px' },
})

const styleObj = computed(() => ({
  width: props.width,
  height: props.height,
  borderRadius: props.radius,
}))
</script>

<style scoped>
.skeleton-block {
  background: linear-gradient(100deg,
    var(--space-surface) 40%,
    var(--border-default) 50%,
    var(--space-surface) 60%);
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}
@keyframes shimmer {
  from { background-position: 120% 0; }
  to { background-position: -20% 0; }
}
</style>
