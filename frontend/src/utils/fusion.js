// ═══════════════════════════════════════════════════
// 织识 · 融合图谱辅助
// 跨论文融合图谱的「来源着色」：节点描边按来源论文映射颜色。
// 单来源节点 → 对应论文序号色；多来源/未知 → 混合亮紫（白）。
// ═══════════════════════════════════════════════════

import { cssVar } from '@/design/tokens'

export const paperPalette = ['#e8453c', '#00d4ff', '#10b981', '#f59e0b', '#a78bfa']

/** 多来源 / 无来源节点的混合描边色（亮紫白） */
export const MIXED_SOURCE_STROKE = '#d8ccff'

/**
 * 由节点 paperIds 数组推导论文序号。
 * 单来源 → 该论文在所选论文列表中的下标；未命中 → 0。
 * 多来源 / 空 → -1（表示混合/未知来源，用混合色）。
 * @param {string[]|undefined} paperIds 后端 fusion 返回的来源论文 id 数组
 * @param {string[]} selectedPapers 本次融合所选论文 id 列表
 * @returns {number}
 */
export function computePaperIndex(paperIds, selectedPapers) {
  if (!Array.isArray(paperIds) || paperIds.length === 0) return -1
  if (paperIds.length > 1) return -1
  const idx = Array.isArray(selectedPapers) ? selectedPapers.indexOf(paperIds[0]) : -1
  return idx === -1 ? 0 : idx
}

/**
 * 节点描边颜色：优先按 paperIndex 着色，其次按概念类型色，最后兜底。
 * 非融合图谱节点没有 paperIndex → 走 d.color 分支，不影响 Workbench。
 * @param {{paperIndex?: number, color?: string}} d 图谱节点
 * @returns {string}
 */
export function nodeStroke(d) {
  const pi = d ? d.paperIndex : undefined
  if (pi !== undefined && pi >= 0) return paperPalette[pi % paperPalette.length]
  if (pi === -1) return MIXED_SOURCE_STROKE
  return (d && d.color) || cssVar('--graph-link', 'rgba(255,255,255,0.35)')
}
