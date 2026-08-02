<template>
  <canvas ref="canvas" class="particle-bg"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvas = ref(null)
let ctx, W, H, particles, mouse, animationId

class Particle {
  constructor() {
    this.reset()
  }
  reset() {
    this.x = Math.random() * W
    this.y = Math.random() * H
    this.vx = (Math.random() - 0.5) * 0.3
    this.vy = (Math.random() - 0.5) * 0.3
    this.r = Math.random() * 1.5 + 0.5
    this.opacity = Math.random() * 0.5 + 0.1
  }
  update() {
    this.x += this.vx
    this.y += this.vy
    if (this.x < 0 || this.x > W) this.vx *= -1
    if (this.y < 0 || this.y > H) this.vy *= -1
  }
  draw() {
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(232,69,60,${this.opacity})`
    ctx.fill()
  }
}

function init() {
  const c = canvas.value
  if (!c) return
  W = c.width = c.offsetWidth
  H = c.height = c.offsetHeight
  ctx = c.getContext('2d')
  particles = Array.from({ length: 60 }, () => new Particle())
  mouse = { x: -100, y: -100 }
}

function animate() {
  ctx.clearRect(0, 0, W, H)

  for (const p of particles) {
    p.update()
    p.draw()

    // 连线：鼠标附近粒子连线
    const dx = mouse.x - p.x
    const dy = mouse.y - p.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist < 150) {
      ctx.beginPath()
      ctx.moveTo(p.x, p.y)
      ctx.lineTo(mouse.x, mouse.y)
      ctx.strokeStyle = `rgba(232,69,60,${0.08 * (1 - dist / 150)})`
      ctx.lineWidth = 0.5
      ctx.stroke()
    }

    // 粒子间连线
    for (const q of particles) {
      if (p === q) continue
      const d = Math.hypot(p.x - q.x, p.y - q.y)
      if (d < 80) {
        ctx.beginPath()
        ctx.moveTo(p.x, p.y)
        ctx.lineTo(q.x, q.y)
        ctx.strokeStyle = `rgba(255,255,255,${0.03 * (1 - d / 80)})`
        ctx.lineWidth = 0.3
        ctx.stroke()
      }
    }
  }

  animationId = requestAnimationFrame(animate)
}

function onMouseMove(e) {
  const rect = canvas.value?.getBoundingClientRect()
  if (rect) {
    mouse.x = e.clientX - rect.left
    mouse.y = e.clientY - rect.top
  }
}

onMounted(() => {
  init()
  animate()
  window.addEventListener('mousemove', onMouseMove)
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('mousemove', onMouseMove)
})
</script>

<style scoped>
.particle-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.5;
}
</style>
