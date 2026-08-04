export const LOW_CONFIDENCE_THRESHOLD = 0.6

export function isLowConfidence(conf) {
  return typeof conf === 'number' && conf < LOW_CONFIDENCE_THRESHOLD
}

// 节点/连线的状态视觉：已确认 → 印章 + 实色；未确认 → 虚线（低置信更虚）
export function nodeStatusVisual(d) {
  const confirmed = d?.status === 'confirmed'
  const low = isLowConfidence(d?.confidence)
  return {
    seal: confirmed,
    dashed: !confirmed,
    opacity: confirmed ? 1 : low ? 0.6 : 0.8,
  }
}

export const STATUS_LABELS = { pending: '待确认', confirmed: '已确认', rejected: '已驳回' }

export function statusLabel(s) {
  return STATUS_LABELS[s] || s || '待确认'
}

export function confPercent(c) {
  return typeof c === 'number' ? `${Math.round(c * 100)}%` : '—'
}
