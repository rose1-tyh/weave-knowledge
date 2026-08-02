<template>
  <div class="graph-page">
    <AppHeader>
      <div class="header-actions">
        <span class="paper-title" v-if="paperTitle">{{ paperTitle }}</span>
        <el-button text @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon> 返回首页
        </el-button>
      </div>
    </AppHeader>

    <div class="graph-body">
      <!-- 加载态 -->
      <div v-if="loading" class="loading-state">
        <div class="loading-icon">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </div>
        <h3>{{ loadingText }}</h3>
        <p class="loading-sub">AI 正在分析论文，提取知识结构...</p>
      </div>

      <!-- 错误态 -->
      <div v-else-if="error" class="error-state">
        <div class="error-icon">!</div>
        <h3>提取失败</h3>
        <p>{{ error }}</p>
        <el-button type="primary" @click="$router.push('/')">返回重试</el-button>
      </div>

      <!-- 图谱 -->
      <template v-else-if="graphData">
        <div class="graph-main">
          <KnowledgeGraph
            :data="graphData"
            :selected-id="selectedNodeId"
            @select-node="onSelectNode"
          />
        </div>
        <aside class="graph-sidebar">
          <ConceptCard
            :concept="selectedConcept"
            :paper-title="paperTitle"
            @close="selectedNodeId = null"
          />
        </aside>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { extractKnowledge, getPaperInfo } from '@/api'
import AppHeader from '@/components/AppHeader.vue'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import ConceptCard from '@/components/ConceptCard.vue'

const route = useRoute()
const paperId = route.params.paperId
const paperTitle = ref(route.query.title || '')

const loading = ref(true)
const loadingText = ref('正在解析论文...')
const error = ref('')
const graphData = ref(null)
const selectedNodeId = ref(null)

const selectedConcept = computed(() => {
  if (!selectedNodeId.value || !graphData.value) return null
  return graphData.value.nodes.find(n => n.id === selectedNodeId.value) || null
})

onMounted(async () => {
  try {
    // 先获取论文信息
    loadingText.value = '正在解析论文...'
    if (!paperTitle.value) {
      try {
        const info = await getPaperInfo(paperId)
        paperTitle.value = info.title
      } catch (_) { /* 忽略 */ }
    }

    // AI 提取
    loadingText.value = 'AI 正在阅读论文，提取核心概念...'
    const data = await extractKnowledge(paperId)
    graphData.value = data
    loading.value = false
  } catch (e) {
    error.value = e.message || '知识提取失败'
    loading.value = false
  }
})

function onSelectNode(nodeId) {
  selectedNodeId.value = nodeId
}
</script>

<style scoped>
.graph-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--paper);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}
.paper-title {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.graph-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.graph-main {
  flex: 1;
  position: relative;
  min-width: 0;
}
.graph-sidebar {
  width: 340px;
  flex-shrink: 0;
  border-left: 1px solid var(--border);
  background: var(--surface);
  overflow-y: auto;
}

/* ── 加载态 ── */
.loading-state,
.error-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
}
.loading-icon {
  display: flex;
  gap: 8px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--seal);
  animation: dot-bounce 1.4s ease-in-out infinite both;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
.loading-state h3,
.error-state h3 {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--ink);
}
.loading-sub {
  font-size: var(--text-sm);
  color: var(--text-muted);
}
.error-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--seal-light);
  color: var(--seal);
  border-radius: 50%;
  font-size: 24px;
  font-weight: 700;
}
.error-state p {
  color: var(--text-secondary);
}
</style>
