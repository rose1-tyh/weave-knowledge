<template>
  <Teleport to="body">
    <Transition name="cmdk-fade">
      <div v-if="open" class="cmdk-overlay" @click.self="$emit('close')">
        <div class="cmdk-panel glass-panel" role="dialog" aria-modal="true" aria-label="全局命令面板">
          <div class="cmdk-head">
            <span class="cmdk-title">织识 · 命令面板</span>
            <span class="cmdk-kbd">↑↓ 选择 · Enter 打开 · Esc 关闭</span>
          </div>
          <input
            ref="inputEl"
            v-model="query"
            class="cmdk-input"
            placeholder="搜索概念、全文，或输入动作名…"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
            @keydown.enter.prevent="choose(highlightIndex)"
            @input="onInput"
          />
          <div class="cmdk-results" ref="listEl">
            <template v-for="group in groups" :key="group.key">
              <div class="cmdk-group">{{ group.label }}</div>
              <button
                v-for="item in group.items"
                :key="item.key"
                class="cmdk-item"
                :class="{ hovered: item.flatIndex === highlightIndex }"
                :data-flat-index="item.flatIndex"
                @mouseenter="highlightIndex = item.flatIndex"
                @click="choose(item.flatIndex)"
              >
                <!-- 概念 -->
                <template v-if="item.kind === 'concept'">
                  <span class="ci-dot" :style="{ background: item.color }"></span>
                  <span class="ci-main">
                    <span class="ci-name">{{ item.name }}</span>
                    <span class="ci-sub ci-snippet" v-html="renderSnippet(item.snippet)"></span>
                  </span>
                  <span class="ci-meta">{{ item.paperTitle }}</span>
                </template>
                <!-- 论文/全文命中 -->
                <template v-else-if="item.kind === 'paper'">
                  <el-icon class="ci-icon"><Document /></el-icon>
                  <span class="ci-main">
                    <span class="ci-name">{{ item.title }}</span>
                    <span class="ci-sub ci-snippet" v-html="renderSnippet(item.snippet)"></span>
                  </span>
                  <span class="ci-meta">全文命中</span>
                </template>
                <!-- 动作 -->
                <template v-else>
                  <el-icon class="ci-icon"><component :is="item.icon" /></el-icon>
                  <span class="ci-main"><span class="ci-name">{{ item.name }}</span></span>
                  <span class="ci-meta">{{ item.hint }}</span>
                </template>
              </button>
            </template>
            <div v-if="query && !flatItems.length && !searching" class="cmdk-empty">
              未找到匹配结果
            </div>
            <div v-if="searching" class="cmdk-empty">搜索中…</div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Document, HomeFilled, Collection, Connection, Upload, DataAnalysis, Setting } from '@element-plus/icons-vue'
import { searchHybrid } from '@/api'
import { renderSnippet } from '@/utils/markdown'

const props = defineProps({
  open: Boolean,
})
const emit = defineEmits(['close'])

const router = useRouter()
const query = ref('')
const results = ref([])
const searching = ref(false)
const highlightIndex = ref(0)
const inputEl = ref(null)
const listEl = ref(null)

// 内置动作：导航快捷入口（始终可用，排在搜索结果之后）
const ACTIONS = [
  { kind: 'action', key: 'act-home', name: '前往首页', hint: '导航', icon: HomeFilled, to: '/' },
  { kind: 'action', key: 'act-library', name: '进入知识库', hint: '导航', icon: Collection, to: '/library' },
  { kind: 'action', key: 'act-explore', name: '全局探索 · 融合图谱', hint: '导航', icon: Connection, to: '/explore' },
  { kind: 'action', key: 'act-import', name: '上传论文 / 导入知识', hint: '动作', icon: Upload, to: '/import' },
  { kind: 'action', key: 'act-analytics', name: '知识洞察 · 统计分析', hint: '导航', icon: DataAnalysis, to: '/analytics' },
  { kind: 'action', key: 'act-settings', name: '设置 · 配置 API Key', hint: '动作', icon: Setting, to: '/settings' },
]

let debounceTimer = null

const flatItems = computed(() => {
  const q = query.value.trim()
  const items = []
  for (const r of results.value) items.push({ ...r, key: `${r.kind}-${r.id}` })
  if (!q) return [...items.filter(r => r.kind === 'concept').slice(0, 5), ...ACTIONS]
  return [...items, ...ACTIONS.filter(a => a.name.toLowerCase().includes(q.toLowerCase()))]
})

const groups = computed(() => {
  const byKind = { concept: { key: 'concept', label: '概念', items: [] },
                   paper: { key: 'paper', label: '论文 · 全文', items: [] },
                   action: { key: 'action', label: '动作', items: [] } }
  flatItems.value.forEach((item, i) => {
    item.flatIndex = i
    byKind[item.kind]?.items.push(item)
  })
  return [byKind.concept, byKind.paper, byKind.action].filter(g => g.items.length)
})

watch(() => props.open, async (opened) => {
  if (opened) {
    query.value = ''
    results.value = []
    highlightIndex.value = 0
    await nextTick()
    inputEl.value?.focus()
  }
})

watch(flatItems, (items) => {
  if (highlightIndex.value >= items.length) highlightIndex.value = 0
})

function onInput() {
  clearTimeout(debounceTimer)
  const q = query.value.trim()
  if (!q) { results.value = []; searching.value = false; return }
  searching.value = true
  debounceTimer = setTimeout(async () => {
    try {
      const data = await searchHybrid(q, 'all', 1, 12)
      results.value = data.results || []
    } catch {
      results.value = []   // 面板内静默：错误不打断输入
    } finally {
      searching.value = false
    }
  }, 250)
}

function move(dir) {
  const n = flatItems.value.length
  if (!n) return
  highlightIndex.value = (highlightIndex.value + dir + n) % n
  nextTick(() => {
    listEl.value?.querySelector(`[data-flat-index="${highlightIndex.value}"]`)
      ?.scrollIntoView({ block: 'nearest' })
  })
}

function choose(index) {
  const item = flatItems.value[index]
  if (!item) return
  emit('close')
  if (item.kind === 'action') {
    router.push(item.to)
  } else if (item.kind === 'concept') {
    router.push({ name: 'Workbench', params: { paperId: item.paperId }, query: { focus: item.id } })
  } else if (item.kind === 'paper') {
    router.push({ name: 'Workbench', params: { paperId: item.id } })
  }
}

defineExpose({ move, choose })
</script>

<style scoped>
.cmdk-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 14vh;
  background: var(--space-overlay);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.cmdk-panel {
  width: 600px;
  max-width: calc(100vw - 48px);
  padding: var(--space-lg);
  background: var(--space-elevated);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5), 0 0 0 1px var(--border-default);
}
.cmdk-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}
.cmdk-title { font-family: var(--font-display); font-size: var(--text-md); color: var(--text-primary); }
.cmdk-kbd {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 2px 6px;
}
.cmdk-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--space-surface);
  color: var(--text-primary);
  font-size: var(--text-base);
  font-family: inherit;
  outline: none;
  margin-bottom: var(--space-sm);
}
.cmdk-input:focus { border-color: var(--vermilion); box-shadow: 0 0 0 2px var(--vermilion-bg); }
.cmdk-results { max-height: 46vh; overflow-y: auto; }
.cmdk-group {
  padding: var(--space-sm) var(--space-xs) 4px;
  font-size: var(--text-xs);
  color: var(--text-muted);
  letter-spacing: 0.08em;
}
.cmdk-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  font-family: inherit;
}
.cmdk-item.hovered { background: var(--hover-tint); }
.ci-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }
.ci-icon { margin-top: 3px; color: var(--text-muted); flex-shrink: 0; }
.ci-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ci-name { font-size: var(--text-sm); color: var(--text-primary); }
.ci-snippet {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ci-snippet :deep(mark) { background: var(--vermilion-bg); color: var(--vermilion); padding: 0 1px; border-radius: 2px; }
.ci-meta {
  flex-shrink: 0;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.cmdk-empty { text-align: center; padding: var(--space-lg); color: var(--text-muted); font-size: var(--text-sm); }

.cmdk-fade-enter-active,
.cmdk-fade-leave-active { transition: opacity var(--ease-out-soft), transform var(--ease-out-soft); }
.cmdk-fade-enter-from,
.cmdk-fade-leave-to { opacity: 0; transform: translateY(-14px) scale(0.98); }
</style>
