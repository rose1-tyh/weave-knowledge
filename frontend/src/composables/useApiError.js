/**
 * 统一 API 错误提示 —— ElMessage 去重（相同文案 1.5s 内不重复弹出）
 *
 * 用法：
 *   const { showError } = useApiError()
 *   try { await api() } catch (e) { showError(e, '保存失败') }
 */
import { ElMessage } from 'element-plus'

let lastMsg = ''
let lastAt = 0

export function showApiError(e, fallback = '操作失败') {
  const msg = (e && e.message) ? e.message : fallback
  const now = Date.now()
  if (msg === lastMsg && now - lastAt < 1500) return
  lastMsg = msg
  lastAt = now
  ElMessage.error(msg)
}

export function useApiError() {
  return { showError: showApiError }
}
