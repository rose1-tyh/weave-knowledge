<template>
  <div ref="el" class="reveal" :class="[visible && 'is-visible', `dir-${direction}`]" :style="{ transitionDelay: delay + 'ms' }">
    <slot />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  delay: { type: Number, default: 0 },
  direction: { type: String, default: 'up' }, // up | left | right
  threshold: { type: Number, default: 0.15 },
})

const el = ref(null)
const visible = ref(false)
let observer = null

onMounted(() => {
  if (!('IntersectionObserver' in window)) { visible.value = true; return }
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) { visible.value = true; observer?.disconnect() }
    },
    { threshold: props.threshold }
  )
  observer.observe(el.value)
})
onUnmounted(() => observer?.disconnect())
</script>

<style scoped>
.reveal {
  opacity: 0;
  transition: opacity 0.7s var(--ease-out-soft), transform 0.7s var(--ease-out-soft);
  will-change: opacity, transform;
}
.reveal.is-visible { opacity: 1; transform: none; }
.dir-up { transform: translateY(28px); }
.dir-left { transform: translateX(-28px); }
.dir-right { transform: translateX(28px); }
</style>
