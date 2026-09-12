/**
 * 织识设计令牌 —— 概念/关系/状态的展示元数据（JS 单一来源）
 *
 * 与后端 services/domain_constants.py 保持对应：
 * 图谱节点着色、编辑器表单、列表徽标、矩阵热力、图例过滤统一引用此处，
 * 修改色板只改这一个文件。
 */

export const TYPE_META = {
  method: { label: '研究方法', color: '#e8453c' },
  theory: { label: '理论基础', color: '#8b5cf6' },
  dataset: { label: '数据集', color: '#10b981' },
  finding: { label: '研究发现', color: '#f59e0b' },
  tool: { label: '工具/系统', color: '#00d4ff' },
}

/** 空间受限场景（图例/搜索徽标）使用的短标签 */
export const TYPE_SHORT = {
  method: '方法',
  theory: '理论',
  dataset: '数据集',
  finding: '发现',
  tool: '工具',
}

export const REL_META = {
  supports: { label: '支撑/验证', color: '#10b981' },
  contradicts: { label: '矛盾/质疑', color: '#e8453c' },
  extends: { label: '扩展/改进', color: '#f59e0b' },
  cites: { label: '引用', color: '#6b7280' },
  uses: { label: '使用', color: '#00d4ff' },
}

export const STATUS_META = {
  pending: { label: '待确认', color: '#f59e0b' },
  confirmed: { label: '已确认', color: '#10b981' },
  rejected: { label: '已驳回', color: '#6b7280' },
}

export const FALLBACK_COLOR = '#6b7280'

/** 概念类型元数据（未知类型兜底） */
export function typeMeta(type) {
  return TYPE_META[type] || { label: type || '未分类', color: FALLBACK_COLOR }
}

/** 关系类型元数据 */
export function relMeta(type) {
  return REL_META[type] || { label: type || '关联', color: FALLBACK_COLOR }
}

/** 审校状态元数据 */
export function statusMeta(status) {
  return STATUS_META[status] || STATUS_META.pending
}

/**
 * 读取 CSS 变量的运行时值 —— 供 D3 SVG 属性等无法直接使用 var() 的场景。
 * 变量未定义（或运行于非 DOM 环境）时返回 fallback。
 */
export function cssVar(name, fallback = '') {
  if (typeof window === 'undefined' || typeof document === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}
