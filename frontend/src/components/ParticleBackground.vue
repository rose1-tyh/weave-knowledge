<template>
  <canvas ref="canvas" class="particle-bg" :style="{ opacity }"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 织识 · 粒子背景
 * 深空星尘：跟随页面 accent 变色的可交互粒子网。
 * 仅使用 canvas 绘制（无第三方依赖），动效天然 GPU 友好。
 */
const props = defineProps({
  /** 主色，任意 hex，默认朱砂 #e8453c */
  accent: { type: String, default: '#e8453c' },
  /** 粒子数量（注意 O(n²) 连线，建议 ≤ 90 保证流畅） */
  density: { type: Number, default: 60 },
  /** 画布整体透明度 */
  opacity: { type: Number, default: 0.5 },
  /** 粒子间连线阈值（px） */
  linkDist: { type: Number, default: 80 },
  /** 鼠标交互半径（px） */
  mouseRadius: { type: Number, default: 150 },
})

const canvas = ref(null)
let ctx, W, H, particles, mouse, animationId, resizeTimer

function accentRgb() {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(props.accent)
  return m
    ? `${parseInt(m[1], 16)},${parseInt(m[2], 16)},${parseInt(m[3], 16)}`
    : '232,69,60'
}

class Particle {
  constructor() { this.reset() }
  reset() {
    this.x = Math.random() * W
    this.y = Math.random() * H
    this.vx = (Math.random() - 0.5) * 0.28
    this.vy = (Math.random() - 0.5) * 0.28
    this.r = Math.random() * 1.6 + 0.6
    this.opacity = Math.random() * 0.55 + 0.15
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
    ctx.fillStyle = `rgba(${accentRgb()},${this.opacity})`
    ctx.fill()
  }
}

function init() {
  const c = canvas.value
  if (!c) return
  W = c.width = c.offsetWidth || window.innerWidth
  H = c.height = c.offsetHeight || window.innerHeight
  ctx = c.getContext('2d')
  const n = Math.max(8, Math.min(120, props.density | 0))
  particles = Array.from({ length: n }, () => new Particle())
  mouse = { x: -1000, y: -1000 }
}

function animate() {
  ctx.clearRect(0, 0, W, H)
  const rgb = accentRgb()
  const linkDist = props.linkDist
  const mouseRadius = props.mouseRadius

  for (const p of particles) {
    p.update()
    p.draw()

    // 鼠标附近的"编织线"
    const dx = mouse.x - p.x
    const dy = mouse.y - p.y
    const dist = Math.hypot(dx, dy)
    if (dist < mouseRadius) {
      ctx.beginPath()
      ctx.moveTo(p.x, p.y)
      ctx.lineTo(mouse.x, mouse.y)
      ctx.strokeStyle = `rgba(${rgb},${0.1 * (1 - dist / mouseRadius)})`
      ctx.lineWidth = 0.6
      ctx.stroke()
    }

    // 粒子间"丝线"（织网感）
    for (const q of particles) {
      if (p === q) continue
      const d = Math.hypot(p.x - q.x, p.y - q.y)
      if (d < linkDist) {
        ctx.beginPath()
        ctx.moveTo(p.x, p.y)
        ctx.lineTo(q.x, q.y)
        ctx.strokeStyle = `rgba(${rgb},${0.05 * (1 - d / linkDist)})`
        ctx.lineWidth = 0.4
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

function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    const c = canvas.value
    if (!c) return
    W = c.width = c.offsetWidth || window.innerWidth
    H = c.height = c.offsetHeight || window.innerHeight
  }, 120)
}

onMounted(() => {
  init()
  animate()
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  clearTimeout(resizeTimer)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.particle-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
</style>
