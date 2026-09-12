<template>
  <div class="weave-extract">
    <div class="we-stage-label">{{ stageLabel }}</div>
    <div class="we-track">
      <div class="we-progress" :style="{ width: progressPct + '%' }"></div>
    </div>
    <div class="we-meta">
      <span v-if="detailText" class="we-detail">{{ detailText }}</span>
      <span class="we-pct">{{ progressPct }}%</span>
    </div>
    <div class="we-nodes">
      <span
        v-for="(n, i) in fakeNodes"
        :key="i"
        class="we-node"
        :class="{ lit: i < litDisplay }"
        :style="{ animationDelay: (i * 0.18) + 's' }"
      ></span>
    </div>
    <Transition name="we-fail-in">
      <div v-if="failed" class="we-failed glass-panel">
        <p class="we-failed-msg">{{ progress?.error || '提取失败，请重试' }}</p>
        <div class="we-failed-actions">
          <el-button size="small" type="primary" data-test="extract-retry" @click="$emit('retry')">重试提取</el-button>
          <el-button size="small" @click="$emit('back')">返回首页</el-button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

/**
 * 提取等待动画：真实进度驱动（progress 快照来自 SSE/轮询）。
 * 快照缺省时回退到演示时间线（组件独立可用）。
 */
const props = defineProps({
  progress: { type: Object, default: null },   // useExtractionProgress 的 snapshot
  failed: Boolean,
})
defineEmits(['retry', 'back'])

const STAGES = [
  { label: '解析文本', dur: 900 },
  { label: '识别概念', dur: 1100 },
  { label: '抽取关系', dur: 1100 },
  { label: '编织成图', dur: 900 },
]
const REAL_LABELS = {
  queued: '排队等待',
  parsing: '解析文档',
  chunking: '切分文本分段',
  extracting: 'AI 概念提取',
  scoring: '置信度交叉评估',
  graphing: '构建知识图谱',
}
const stage = ref(0)
const stageProgress = ref(0)
const litCount = ref(0)
const fakeNodes = Array.from({ length: 8 })
let timer = null

const real = computed(() => props.progress && props.progress.status !== 'pending')
const stageLabel = computed(() => {
  if (real.value) return REAL_LABELS[props.progress.stage] || '准备中'
  return STAGES[stage.value].label
})
const progressPct = computed(() => {
  if (real.value) return Math.round(Math.min(1, props.progress.progress || 0) * 100)
  return Math.round(((stage.value + stageProgress.value) / STAGES.length) * 100)
})
const detailText = computed(() => {
  if (!real.value) return ''
  const d = props.progress.detail
  if (props.progress.stage === 'extracting' && d) return `第 ${d} 段`
  if (props.progress.stage === 'chunking' && d) return `共 ${d} 段`
  return props.progress.message || ''
})
// 节点点亮跟随真实进度；无进度时按时间线推进
const litFromProgress = computed(() => Math.floor((progressPct.value / 100) * fakeNodes.length))
const litDisplay = computed(() => (real.value ? litFromProgress.value : litCount.value))

function tick() {
  // 到达末阶段即停在末尾（标签不变、进度满、节点全亮），stage 不再增长
  if (stage.value >= STAGES.length - 1) {
    stageProgress.value = 1
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
  z-index: 30;
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
  background: var(--border-default);
  overflow: hidden;
}
.we-progress {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--vermilion), var(--amber));
  box-shadow: var(--vermilion-glow);
  transition: width 400ms var(--ease-out-soft);
}

/* 阶段明细 + 百分比 */
.we-meta {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  min-height: 18px;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}
.we-pct {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
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

/* 失败面板 */
.we-failed {
  position: absolute;
  bottom: 18%;
  padding: var(--space-md) var(--space-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  background: var(--space-elevated);
  animation: we-fail-in 400ms var(--ease-out-soft) both;
}
.we-failed-msg {
  font-size: var(--text-sm);
  color: var(--vermilion);
  max-width: 360px;
  text-align: center;
}
.we-failed-actions { display: flex; gap: var(--space-sm); }
@keyframes we-fail-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
