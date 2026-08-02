<template>
  <div class="weave-extract">
    <div class="we-stage-label">{{ stageLabel }}</div>
    <div class="we-track">
      <div class="we-progress" :style="{ width: progressPct + '%' }"></div>
    </div>
    <div class="we-nodes">
      <span
        v-for="(n, i) in fakeNodes"
        :key="i"
        class="we-node"
        :class="{ lit: i < litCount }"
        :style="{ animationDelay: (i * 0.18) + 's' }"
      ></span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const STAGES = [
  { label: '解析文本', dur: 900 },
  { label: '识别概念', dur: 1100 },
  { label: '抽取关系', dur: 1100 },
  { label: '编织成图', dur: 900 },
]
const stage = ref(0)
const stageProgress = ref(0)
const litCount = ref(0)
const fakeNodes = Array.from({ length: 8 })
let timer = null

const stageLabel = computed(() => STAGES[stage.value].label)
const progressPct = computed(() => ((stage.value + stageProgress.value) / STAGES.length) * 100)

function tick() {
  if (stage.value >= STAGES.length) {
    litCount.value = fakeNodes.length
    return
  }
  stageProgress.value += 0.03
  litCount.value = Math.min(
    fakeNodes.length,
    Math.floor(stage.value * 2.5 + stageProgress.value * 2.5)
  )
  if (stageProgress.value >= 1) { stageProgress.value = 0; stage.value += 1 }
}

onMounted(() => { timer = setInterval(tick, 30) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.weave-extract {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-lg);
  background: var(--space-deep);
  color: var(--text-primary);
  overflow: hidden;
}

/* 标签：朱砂霓虹发光，仅 transform/opacity 动效 */
.we-stage-label {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  letter-spacing: 0.24em;
  padding-left: 0.24em;
  color: var(--text-primary);
  text-shadow: var(--vermilion-glow);
  animation: we-label-in 500ms var(--ease-out-soft) both;
}
@keyframes we-label-in {
  from { opacity: 0; transform: translateY(10px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* 进度轨道 */
.we-track {
  width: 260px;
  height: 3px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.we-progress {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--vermilion), var(--amber));
  box-shadow: var(--vermilion-glow);
}

/* 概念节点：逐颗点亮 + 呼吸脉冲（只用 transform/opacity） */
.we-nodes {
  display: flex;
  gap: var(--space-md);
}
.we-node {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--border-default);
  animation: we-node-pulse 1.8s var(--ease-out-soft) infinite both;
}
.we-node.lit {
  background: var(--vermilion);
  box-shadow: var(--vermilion-glow);
}
@keyframes we-node-pulse {
  0%, 100% { opacity: 0.45; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.05); }
}
</style>
