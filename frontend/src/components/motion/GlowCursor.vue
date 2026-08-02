<template>
  <div v-if="enabled" class="glow-cursor" :style="{ transform: `translate(${x}px, ${y}px)` }"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const enabled = ref(false)
const x = ref(-100)
const y = ref(-100)
let raf = 0

function onMove(e) {
  const move = () => {
    x.value = e.clientX
    y.value = e.clientY
  }
  if (raf) cancelAnimationFrame(raf)
  raf = requestAnimationFrame(move)
}

onMounted(() => {
  // 仅在不支持触控的设备启用，避免移动端干扰
  if (!window.matchMedia('(pointer: coarse)').matches) {
    enabled.value = true
    window.addEventListener('mousemove', onMove, { passive: true })
  }
})
onUnmounted(() => {
  window.removeEventListener('mousemove', onMove)
  cancelAnimationFrame(raf)
})
</script>

<style scoped>
.glow-cursor {
  position: fixed;
  top: 0; left: 0;
  width: 400px; height: 400px;
  border-radius: 50%;
  pointer-events: none;
  z-index: 5;
  background: radial-gradient(circle, rgba(232,69,60,0.06) 0%, transparent 60%);
  transform: translate(-200px, -200px);
  transition: left 0s;
  will-change: transform;
}
</style>
