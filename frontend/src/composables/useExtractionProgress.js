/**
 * 提取实时进度 —— SSE 优先（GET /api/extract/progress/{id}），异常时自动降级轮询
 *
 * snapshot 与后端 extract_tasks 状态快照同构：
 * { status, stage, progress, detail, message, error }
 * status: pending / processing / done / failed / not_found
 * stage:  queued / parsing / chunking / extracting / scoring / graphing / done / failed
 */
import { ref, computed, onUnmounted } from 'vue'
import { getExtractStatus } from '@/api'

export const STAGE_LABELS = {
  queued: '排队等待',
  parsing: '解析文档',
  chunking: '切分文本分段',
  extracting: 'AI 概念提取',
  scoring: '置信度交叉评估',
  graphing: '构建知识图谱',
  done: '提取完成',
  failed: '提取失败',
}

const TERMINAL = ['done', 'failed', 'not_found']

export function useExtractionProgress() {
  const snapshot = ref({
    status: 'pending', stage: '', progress: 0, detail: '', message: '', error: '',
  })
  const active = ref(false)

  let es = null
  let pollTimer = null

  const stageLabel = computed(() => STAGE_LABELS[snapshot.value.stage] || '准备中')
  const percent = computed(() => Math.round(Math.min(1, snapshot.value.progress || 0) * 100))

  function apply(data) {
    snapshot.value = { ...snapshot.value, ...data }
  }

  function stop() {
    active.value = false
    if (es) { es.close(); es = null }
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  }

  function finish(status, callbacks, data) {
    stop()
    if (status === 'done') callbacks?.onDone?.(data)
    else callbacks?.onFailed?.(data)
  }

  function startPolling(paperId, callbacks, interval = 2000) {
    if (pollTimer) return
    pollTimer = setInterval(async () => {
      try {
        const st = await getExtractStatus(paperId)
        apply(st)
        if (TERMINAL.includes(st.status)) finish(st.status, callbacks, st)
      } catch { /* 网络抖动：下一轮重试 */ }
    }, interval)
  }

  function start(paperId, callbacks = {}) {
    stop()
    active.value = true
    // SSE：服务端变化即推送、15s 心跳、终态自关闭；断连且非终态时降级轮询
    if (typeof EventSource !== 'undefined') {
      try {
        es = new EventSource(`/api/extract/progress/${paperId}`)
        es.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data)
            apply(data)
            if (TERMINAL.includes(data.status)) finish(data.status, callbacks, data)
          } catch { /* 忽略坏帧 */ }
        }
        es.onerror = () => {
          // 终态自关闭或浏览器重连间隙：非终态才降级轮询
          if (!TERMINAL.includes(snapshot.value.status)) {
            if (es) { es.close(); es = null }
            startPolling(paperId, callbacks)
          }
        }
        return
      } catch { /* EventSource 构造失败 → 轮询 */ }
    }
    startPolling(paperId, callbacks)
  }

  onUnmounted(stop)

  return { snapshot, active, stageLabel, percent, start, stop }
}
