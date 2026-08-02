<template>
  <span class="count-up">{{ formatted }}</span>
</template>

<script setup>
import { ref, watch, computed, onUnmounted } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  duration: { type: Number, default: 1200 },
  decimals: { type: Number, default: 0 },
})

const current = ref(0)
let raf = 0

function animate() {
  cancelAnimationFrame(raf)
  const start = performance.now()
  const from = current.value
  const diff = props.value - from
  const tick = (now) => {
    const p = Math.min((now - start) / props.duration, 1)
    const eased = 1 - Math.pow(1 - p, 3) // easeOutCubic
    current.value = from + diff * eased
    if (p < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}

watch(() => props.value, animate, { immediate: true })
onUnmounted(() => cancelAnimationFrame(raf))

const formatted = computed(() =>
  current.value.toLocaleString('en-US', {
    minimumFractionDigits: props.decimals,
    maximumFractionDigits: props.decimals,
  })
)

defineExpose({ current })
</script>
