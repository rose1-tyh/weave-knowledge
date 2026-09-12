/**
 * 轻量 SVG 图表工具 —— 洞察页手写图表的数据变换与几何计算
 * 不引入图表库：环图弧路径 / 条形宽度缩放均为纯函数，便于测试与主题化。
 */

const rad = (deg) => ((deg - 90) * Math.PI) / 180

/**
 * 环图切片路径（外半径 r2、内半径 r1，角度制，0° 指向正上方）
 * 全圆（≥360°）时拆为两段半圆路径，避免 arc 命令退化
 */
export function donutSlice(cx, cy, r1, r2, a0, a1) {
  if (a1 - a0 >= 359.99) {
    const half = donutSlice(cx, cy, r1, r2, a0, a0 + 179.99)
      + donutSlice(cx, cy, r1, r2, a0 + 180, a1)
    return half
  }
  const x = (r, a) => (cx + r * Math.cos(rad(a))).toFixed(3)
  const y = (r, a) => (cy + r * Math.sin(rad(a))).toFixed(3)
  const large = a1 - a0 > 180 ? 1 : 0
  return (
    `M${x(r2, a0)},${y(r2, a0)}`
    + ` A${r2},${r2} 0 ${large} 1 ${x(r2, a1)},${y(r2, a1)}`
    + ` L${x(r1, a1)},${y(r1, a1)}`
    + ` A${r1},${r1} 0 ${large} 0 ${x(r1, a0)},${y(r1, a0)} Z`
  )
}

/** 计数列表 → 环图切片（含起止角与百分比），列表按数值降序更直观 */
export function buildDonutSlices(counts, { pad = 0.6 } = {}) {
  const total = counts.reduce((s, c) => s + c.value, 0)
  if (!total) return []
  const usable = 360 - pad * counts.length
  let angle = 0
  return counts.map((c) => {
    const sweep = (c.value / total) * usable
    const slice = { ...c, a0: angle, a1: angle + sweep, percent: c.value / total }
    angle += sweep + pad
    return slice
  })
}

/** 条形宽度：按最大值等比缩放到 maxWidth；0 值不画，非零保证最小 2px 可见 */
export function barWidth(value, max, maxWidth) {
  if (max <= 0 || value <= 0) return 0
  return Math.max(2, Math.round((value / max) * maxWidth))
}
