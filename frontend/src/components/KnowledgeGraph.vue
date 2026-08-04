<template>
  <div ref="container" class="kg-container">
    <div ref="tooltip" class="graph-tooltip"></div>
    <svg ref="svgEl"></svg>
    <!-- 图例 -->
    <div class="kg-legend glass-panel">
      <div class="legend-row">
        <span class="legend-label">概念</span>
        <span v-for="t in conceptTypes" :key="t.key" class="legend-chip" :class="{ active: graphStore.filterType === t.key }" @click="graphStore.toggleFilter(t.key)">
          <i :style="{ background: t.color, boxShadow: `0 0 6px ${t.color}` }"></i>{{ t.label }}
        </span>
      </div>
      <div class="legend-row">
        <span class="legend-label">状态</span>
        <span class="legend-chip"><i class="legend-seal"></i>人工验证</span>
        <span class="legend-chip"><i class="legend-dash"></i>待确认/低置信</span>
      </div>
      <div class="legend-row">
        <span class="legend-label">关系</span>
        <span v-for="t in relationTypes" :key="t.key" class="legend-chip">
          <i :style="{ background: t.color }"></i>{{ t.label }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as d3 from 'd3'
import { nodeStroke } from '@/utils/fusion'
import { nodeStatusVisual } from '@/utils/confidence'
import { useGraphStore } from '@/stores/graph'

const props = defineProps({
  data: { type: Object, required: true },
  selectedId: { type: String, default: null },
  editing: Boolean,
})

const emit = defineEmits(['select-node', 'select-link', 'add-relation', 'edit-node', 'box-select'])

const container = ref(null)
const svgEl = ref(null)
const tooltip = ref(null)

const graphStore = useGraphStore()

const conceptTypes = [
  { key: 'method', label: '方法', color: '#e8453c' },
  { key: 'theory', label: '理论', color: '#8b5cf6' },
  { key: 'dataset', label: '数据集', color: '#10b981' },
  { key: 'finding', label: '发现', color: '#f59e0b' },
  { key: 'tool', label: '工具', color: '#00d4ff' },
]
const relationTypes = [
  { key: 'supports', label: '支撑', color: '#10b981' },
  { key: 'contradicts', label: '矛盾', color: '#e8453c' },
  { key: 'extends', label: '扩展', color: '#f59e0b' },
  { key: 'cites', label: '引用', color: '#6b7280' },
  { key: 'uses', label: '使用', color: '#00d4ff' },
]

let simulation = null
let resizeObserver = null
let dragSourceNode = null
let zoomBehavior = null
let currentTransform = null
let hoveredLink = null
let boxSelect = null        // 框选起点（svg 屏幕坐标）
let boxRect = null          // 框选矩形 d3 selection
let dragGroupStart = null   // 多选批量移动的起始位置快照

onMounted(() => {
  render()
  resizeObserver = new ResizeObserver(() => render())
  resizeObserver.observe(container.value)
})
onUnmounted(() => {
  if (simulation) simulation.stop()
  if (resizeObserver) resizeObserver.disconnect()
  cancelBoxSelect() // 卸载时清理可能残留的 window mousemove/mouseup 监听
})

watch(() => props.data, () => { render(); applyFilter() })
watch(() => props.selectedId, (id) => { highlightNode(id); refreshSelectionVisual() })
// 编辑模式切换时更新 zoom filter（排除背景 mousedown 以便框选，而非平移）
watch(() => props.editing, () => {
  if (zoomBehavior) zoomBehavior.filter(shouldZoom)
})
// 过滤状态存 graph store（规格 F1）：Workbench/Explore 共享、跨视图切换保持；变化即重算视觉
watch(() => graphStore.filterType, () => applyFilter())
// 多选集合变化 → 刷新节点选中视觉
watch(() => graphStore.selectedNodeIds, refreshSelectionVisual, { deep: true })

// d3-zoom 过滤：普通模式恢复默认检查（!event.button 拦右键/中键拖拽，Ctrl+手势排除双重缩放），
// 编辑模式额外排除 mousedown（背景拖拽留给框选而非平移）；wheel 始终放行。
function shouldZoom(event) {
  return (props.editing ? event.type !== 'mousedown' : (!event.ctrlKey || event.type === 'wheel'))
    && !event.button
}

function render() {
  if (!container.value || !props.data) return
  // 重建前先停止旧力模拟，避免 d3-timer 持有旧引用持续 tick（侧栏折叠/转场会提高 render 频率）
  if (simulation) simulation.stop()
  // 重建前若框选仍在进行则取消（resize/数据刷新可能触发 render）
  cancelBoxSelect()

  const el = container.value
  const W = el.clientWidth
  const H = el.clientHeight
  const { nodes, links } = props.data
  if (!nodes.length) return
  hoveredLink = null

  const svg = d3.select(svgEl.value)
  svg.selectAll('*').remove()
  svg.attr('width', W).attr('height', H)

  // 背景微粒网格
  const defs = svg.append('defs')
  defs.append('pattern').attr('id', 'grid').attr('width', 24).attr('height', 24).attr('patternUnits', 'userSpaceOnUse')
    .append('circle').attr('cx', 12).attr('cy', 12).attr('r', 0.6).attr('fill', 'rgba(255,255,255,0.06)')
  svg.append('rect').attr('width', W).attr('height', H).attr('fill', 'url(#grid)')

  // 发光滤镜
  defs.append('filter').attr('id', 'glow-vermilion')
    .html('<feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>')
  defs.append('filter').attr('id', 'glow-cyan')
    .html('<feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>')

  const g = svg.append('g')
  zoomBehavior = d3.zoom()
    .scaleExtent([0.15, 5])
    // 组合 d3-zoom 默认过滤（!event.button 拦右键/中键拖拽、!event.ctrlKey 排除 Ctrl+手势），
    // 编辑模式额外排除 mousedown：空白处拖拽留给框选，而不是背景平移
    .filter(shouldZoom)
    .on('zoom', e => {
      currentTransform = e.transform
      g.attr('transform', e.transform)
    })
  svg.call(zoomBehavior)
  // 优先恢复上次缩放状态，否则居中初始化
  if (currentTransform) {
    svg.call(zoomBehavior.transform, currentTransform)
  } else {
    currentTransform = d3.zoomIdentity.translate(W / 2, H / 2)
    svg.call(zoomBehavior.transform, currentTransform)
  }

  // 编辑模式：svg 空白 mousedown → 框选（节点自身的 drag 会 stopImmediatePropagation，不会触发到这里）
  svg.on('mousedown', onSvgMouseDown)

  // 力模拟
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(140))
    .force('charge', d3.forceManyBody().strength(-500))
    .force('center', d3.forceCenter(0, 0))
    .force('collision', d3.forceCollide(50))

  // 边
  const linkG = g.append('g')
  const linkLines = linkG.selectAll('line').data(links).join('line')
    .attr('class', d => nodeStatusVisual(d).dashed ? 'link-dashed' : 'link-solid')
    .attr('data-role', 'link')
    .attr('stroke', d => d.color || 'rgba(255,255,255,0.2)')
    .attr('stroke-opacity', 0.6)
    .attr('stroke-width', d => d.type === 'contradicts' ? 2 : 1.2)
    .attr('opacity', d => nodeStatusVisual(d).opacity)
    .style('cursor', 'pointer')
    .on('click', (e, d) => {
      e.stopPropagation()
      emit('select-link', links.indexOf(d))
    })
    .on('mouseenter', function (e, d) {
      hoveredLink = d
      d3.select(this)
        .attr('stroke-width', d.type === 'contradicts' ? 3.5 : 2.7)
        .attr('stroke-opacity', 0.9)
      tip.textContent = d.type || '关系'
      tip.classList.add('visible')
    })
    .on('mousemove', e => {
      tip.style.left = (e.offsetX + 14) + 'px'
      tip.style.top = (e.offsetY - 10) + 'px'
    })
    .on('mouseleave', function (e, d) {
      hoveredLink = null
      d3.select(this)
        .attr('stroke-width', d.type === 'contradicts' ? 2 : 1.2)
        .attr('stroke-opacity', 0.6)
      tip.classList.remove('visible')
    })

  // 节点组
  const nodeG = g.append('g')
  const nodeGroups = nodeG.selectAll('g').data(nodes).join('g')
    .attr('data-role', 'node')
    .attr('cursor', props.editing ? 'crosshair' : 'pointer')
    .call(d3.drag()
      .on('start', (e, d) => {
        if (props.editing) { dragSourceNode = d; return }
        if (!e.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
        // 多选批量移动：拖动的节点在多选集合内且多选数量 > 1 → 记录整组初始位置
        if (graphStore.selectedNodeIds.length > 1 && graphStore.selectedNodeIds.includes(d.id)) {
          dragGroupStart = props.data.nodes
            .filter(n => graphStore.selectedNodeIds.includes(n.id))
            .map(n => ({ id: n.id, x: n.x, y: n.y }))
        }
      })
      .on('drag', (e, d) => {
        if (props.editing) return
        if (dragGroupStart) {
          // 批量移动：把位移 delta 应用到全部选中节点
          const orig = dragGroupStart.find(p => p.id === d.id)
          if (!orig) { d.fx = e.x; d.fy = e.y; return }
          const dx = e.x - orig.x
          const dy = e.y - orig.y
          for (const p of dragGroupStart) {
            const n = props.data.nodes.find(nn => nn.id === p.id)
            if (n) { n.fx = p.x + dx; n.fy = p.y + dy }
          }
          return
        }
        d.fx = e.x; d.fy = e.y
      })
      .on('end', (e, d) => {
        // 编辑模式：源节点拖拽到另一节点上方松手 → 创建关系（命中测试；可能未命中，属正常）。
        // 注意 d3-drag 的 end 事件始终携带“手势起点”节点 datum（即源节点），
        // 因此目标节点需用指针命中测试（elementsFromPoint）定位，而非事件自身 datum。
        if (props.editing && dragSourceNode) {
          const target = nodeAtPoint(e.sourceEvent?.clientX, e.sourceEvent?.clientY, d)
          if (target) emit('add-relation', { source: d.id, target: target.id })
        }
        dragSourceNode = null
        // 无条件清理：复位仿真热度、释放全部 fx/fy、清空组移动快照，
        // 避免拖拽后仿真停在 alpha floor 或节点被钉住（编辑模式同样适用）。
        if (!e.active) simulation.alphaTarget(0)
        if (dragGroupStart) {
          for (const p of dragGroupStart) {
            const n = props.data.nodes.find(nn => nn.id === p.id)
            if (n) { n.fx = null; n.fy = null }
          }
          dragGroupStart = null
        }
        d.fx = null; d.fy = null
      })
    )

  // 外圈光晕
  nodeGroups.append('circle')
    .attr('r', 30)
    .attr('fill', d => d.color)
    .attr('opacity', 0.08)

  // 节点主体（描边支持融合来源着色：paperIndex → 论文色；-1 → 混合亮紫）
  nodeGroups.append('circle')
    .attr('r', 18)
    .attr('fill', '#111827')
    .attr('stroke', d => nodeStroke(d))
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', d => nodeStatusVisual(d).dashed ? '4,3' : null)
    .attr('opacity', d => nodeStatusVisual(d).opacity)
    .attr('style', d => `filter: drop-shadow(0 0 6px ${d.color})`)

  // 选中发光环
  nodeGroups.append('circle')
    .attr('r', 22)
    .attr('fill', 'none')
    .attr('stroke', d => d.color)
    .attr('stroke-width', 1)
    .attr('stroke-opacity', 0)
    .attr('class', 'selected-ring')

  // 文字
  nodeGroups.append('text')
    .text(d => d.name.length > 5 ? d.name.slice(0, 5) + '…' : d.name)
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('fill', '#fff')
    .attr('font-size', d => d.name.length > 5 ? 10 : 12)
    .attr('font-weight', 500)
    .attr('pointer-events', 'none')
    .attr('style', 'text-shadow: 0 0 4px rgba(0,0,0,0.8)')

  // 已确认节点印章（append 在 text 之后，位于节点组最上层）
  const sealG = nodeGroups.filter(d => nodeStatusVisual(d).seal).append('g')
    .attr('class', 'node-seal')
    .attr('pointer-events', 'none')
  sealG.append('rect')
    .attr('x', -7).attr('y', 20).attr('width', 14).attr('height', 12).attr('rx', 2)
    .attr('fill', 'none').attr('stroke', '#e8453c').attr('stroke-width', 1.2)
  sealG.append('text')
    .attr('x', 0).attr('y', 29.5)
    .attr('text-anchor', 'middle').attr('font-size', 8).attr('font-weight', 700)
    .attr('fill', '#e8453c')
    .text('验')

  // 提示信息
  const tip = tooltip.value
  nodeGroups.on('click', (e, d) => {
    if (props.editing) return
    e.stopPropagation()
    emit('select-node', d.id)
  })
  nodeGroups.on('dblclick', (e, d) => {
    if (props.editing) emit('edit-node', d.id)
  })
  nodeGroups.on('mouseenter', (e, d) => {
    if (props.editing) {
      tip.textContent = `${d.name} — 拖拽至另一节点创建关系`
    } else {
      tip.textContent = `${d.name}\n${d.definition || ''}`
    }
    tip.classList.add('visible')
  })
  nodeGroups.on('mousemove', e => {
    tip.style.left = (e.offsetX + 14) + 'px'
    tip.style.top = (e.offsetY - 10) + 'px'
  })
  nodeGroups.on('mouseleave', () => tip.classList.remove('visible'))

  // 右键菜单
  nodeGroups.on('contextmenu', (e, d) => {
    e.preventDefault()
    if (props.editing) {
      emit('select-node', d.id)
    }
  })

  svg.on('click', () => { if (!props.editing) emit('select-node', null) })

  // tick
  simulation.on('tick', () => {
    linkLines
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
      .attr('stroke-width', d => {
        const base = d.type === 'contradicts' ? 2 : 1.2
        return hoveredLink === d ? base + 1.5 : base
      })
      .attr('stroke-opacity', d => hoveredLink === d ? 0.9 : 0.6)
    nodeGroups.attr('transform', d => `translate(${d.x},${d.y})`)
  })

  highlightNode(props.selectedId)
  refreshSelectionVisual()
  applyFilter()
}

// ── 图例类型过滤：只改 opacity，不重排布局；过滤状态由 graph store 持有（规格 F1）──
function applyFilter() {
  const svg = d3.select(svgEl.value)
  const f = graphStore.filterType
  svg.selectAll('g g[data-role=node]').attr('opacity', function () {
    const d = d3.select(this).datum()
    return f && d.type !== f ? 0.12 : 1
  })
  svg.selectAll('line[data-role=link]').attr('opacity', function () {
    const d = d3.select(this).datum()
    // 以状态透明度为基数（已确认实色/未确认按置信度虚化），过滤时再叠加
    const base = nodeStatusVisual(d).opacity
    if (!f) return base
    const src = typeof d.source === 'object' ? d.source : null
    const tgt = typeof d.target === 'object' ? d.target : null
    const srcOk = src && src.type === f
    const tgtOk = tgt && tgt.type === f
    return srcOk || tgtOk ? base : 0.05
  })
}

function highlightNode(id) {
  const svg = d3.select(svgEl.value)
  svg.selectAll('g g .selected-ring')
    .attr('stroke-opacity', function () {
      const d = d3.select(this.parentNode).datum()
      return d && d.id === id ? 0.4 : 0
    })
    .attr('style', function () {
      const d = d3.select(this.parentNode).datum()
      return d && d.id === id ? `filter: drop-shadow(0 0 22px ${d.color})` : null
    })
  svg.selectAll('g g circle:nth-child(2)')
    .attr('stroke-width', function () {
      const d = d3.select(this.parentNode).datum()
      return d && d.id === id ? 3 : 2
    })
    .attr('style', function () {
      const d = d3.select(this.parentNode).datum()
      const selected = d && d.id === id
      return `filter: drop-shadow(0 0 ${selected ? 14 : 6}px ${d.color})`
    })
}

// ── 多选选中视觉：复用 .selected-ring，多选节点用静态低亮、单选用动画高亮 ──
function refreshSelectionVisual() {
  const el = svgEl.value
  if (!el) return
  const multi = graphStore.selectedNodeIds || []
  const single = props.selectedId
  d3.select(el).selectAll('g g .selected-ring')
    .attr('stroke-opacity', function () {
      const d = d3.select(this.parentNode).datum()
      if (single && d.id === single) return 0.4
      if (multi.length && multi.includes(d.id)) return 0.3
      return 0
    })
    .attr('style', function () {
      const d = d3.select(this.parentNode).datum()
      if (single && d.id === single) return `filter: drop-shadow(0 0 22px ${d.color})`
      if (multi.length && multi.includes(d.id)) return `filter: drop-shadow(0 0 12px ${d.color})`
      return null
    })
}

// 编辑模式拖拽建关系的目标命中：返回指针下“非源节点”的节点 datum（无则 null）。
// 用 document.elementsFromPoint 取指针下所有元素，遍历找第一个 [data-role=node] 且
// datum.id !== 源节点 id 的元素——源节点若在上层盖住目标（DOM 更靠后），仍能命中其下目标。
// 兼容缩放平移后的坐标（基于渲染几何做真实 DOM 命中）。
function nodeAtPoint(clientX, clientY, source) {
  if (typeof clientX !== 'number' || typeof clientY !== 'number') return null
  const els = document.elementsFromPoint(clientX, clientY) || []
  for (const el of els) {
    const nodeEl = el && el.closest ? el.closest('[data-role="node"]') : null
    if (!nodeEl) continue
    const datum = d3.select(nodeEl).datum()
    if (datum && datum.id !== source?.id) return datum
  }
  return null
}

// ── 编辑模式框选：svg 空白 mousedown → 虚线矩形 → mouseup 收集矩形内节点 ──
function cancelBoxSelect() {
  if (boxRect) { boxRect.remove(); boxRect = null }
  boxSelect = null
  window.removeEventListener('mousemove', onBoxMouseMove)
  window.removeEventListener('mouseup', onBoxMouseUp)
}

// 框选结束后的尾随 click 抑制：注册一次性捕获 click，阻止其冒泡到 svg 的 click handler。
// 现状编辑模式 svg click 本就是 no-op，此为保险丝——即使将来某条路径让背景 click emit，也不会误清多选。
function suppressTrailingClick() {
  const handler = (e) => {
    e.preventDefault()
    e.stopImmediatePropagation()
    window.removeEventListener('click', handler, true)
  }
  window.addEventListener('click', handler, true)
  setTimeout(() => window.removeEventListener('click', handler, true), 0)
}

function onSvgMouseDown(e) {
  if (!props.editing) return
  if (e.button !== 0) return // 只响应左键，避免右键触发框选/原生菜单
  // 只响应背景 mousedown：节点/连线上的事件忽略（节点 drag 已 stopImmediatePropagation）
  const t = e.target
  if (t && t.closest && (t.closest('[data-role="node"]') || t.closest('[data-role="link"]'))) return
  const el = svgEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  boxSelect = { startX: x, startY: y }
  boxRect = d3.select(el).append('rect')
    .attr('class', 'box-select')
    .attr('x', x).attr('y', y)
    .attr('width', 0).attr('height', 0)
    .attr('fill', 'rgba(232, 69, 60, 0.10)')
    .attr('stroke', '#e8453c')
    .attr('stroke-width', 1)
    .attr('stroke-dasharray', '6 4')
    .attr('pointer-events', 'none')
  window.addEventListener('mousemove', onBoxMouseMove)
  window.addEventListener('mouseup', onBoxMouseUp)
}

function onBoxMouseMove(e) {
  if (!boxSelect || !boxRect) return
  const el = svgEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  const startX = boxSelect.startX
  const startY = boxSelect.startY
  boxRect
    .attr('x', Math.min(x, startX))
    .attr('y', Math.min(y, startY))
    .attr('width', Math.abs(x - startX))
    .attr('height', Math.abs(y - startY))
}

function onBoxMouseUp(e) {
  if (!boxSelect) return
  const el = svgEl.value
  if (el) {
    const rect = el.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const startX = boxSelect.startX
    const startY = boxSelect.startY
    const minX = Math.min(x, startX)
    const minY = Math.min(y, startY)
    const w = Math.abs(x - startX)
    const h = Math.abs(y - startY)
    const ids = []
    // 忽略误触的小矩形
    if (w > 2 && h > 2 && props.data?.nodes) {
      // 节点世界坐标 → 屏幕坐标（应用缩放平移），判断是否落在矩形内
      const t = currentTransform || d3.zoomIdentity
      for (const n of props.data.nodes) {
        const sx = n.x * t.k + t.x
        const sy = n.y * t.k + t.y
        if (sx >= minX && sx <= minX + w && sy >= minY && sy <= minY + h) {
          ids.push(n.id)
        }
      }
    }
    boxRect?.remove()
    boxRect = null
    boxSelect = null
    window.removeEventListener('mousemove', onBoxMouseMove)
    window.removeEventListener('mouseup', onBoxMouseUp)
    suppressTrailingClick() // 保险丝：吞掉本次框选手势产生的尾随 click
    if (ids.length) emit('box-select', ids)
  } else {
    cancelBoxSelect()
  }
}

// ── 工具栏缩放控制 ──
function zoomBy(factor) {
  if (!zoomBehavior || !svgEl.value) return
  d3.select(svgEl.value).transition().duration(200).call(zoomBehavior.scaleBy, factor)
}
function resetZoom() {
  if (!zoomBehavior || !svgEl.value || !container.value) return
  const W = container.value.clientWidth
  const H = container.value.clientHeight
  d3.select(svgEl.value).transition().duration(200)
    .call(zoomBehavior.transform, d3.zoomIdentity.translate(W / 2, H / 2))
}

// ── 搜索定位：匹配到概念名后，居中聚焦到该节点 ──
function zoomToNode(id) {
  if (!props.data) return
  const node = props.data.nodes.find(n => n.id === id)
  if (!node || !zoomBehavior || !container.value) return
  const W = container.value.clientWidth
  const H = container.value.clientHeight
  const target = { x: node.x ?? 0, y: node.y ?? 0 }
  const k = currentTransform?.k ?? 1
  const k2 = Math.max(k, 1.6)
  const t = d3.zoomIdentity.translate(W / 2 - target.x * k2, H / 2 - target.y * k2).scale(k2)
  d3.select(svgEl.value).transition().duration(500)
    .call(zoomBehavior.transform, t)
  emit('select-node', id)  // 让侧栏显示详情
}
defineExpose({ zoomBy, resetZoom, zoomToNode })
</script>

<style scoped>
.kg-container {
  width: 100%; height: 100%; position: relative; overflow: hidden;
  background:
    radial-gradient(ellipse at 50% 40%, rgba(201,162,39,0.06), transparent 60%),
    var(--space-deep);
}
.kg-container::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background-image: var(--grain-overlay);
}
.kg-container svg { display: block; }

/* 编辑模式框选矩形：即时绘制，非动画 */
:deep(.box-select) {
  shape-rendering: crispEdges;
  pointer-events: none;
}

/* 节点脉冲动画 */
:deep(g g circle:nth-child(2)) {
  animation: node-pulse 3s ease-in-out infinite;
}
@keyframes node-pulse {
  0%, 100% { r: 18; }
  50% { r: 20; }
}

/* 连线流动动画：已确认实线不流动；未确认虚线流动 */
:deep(g line.link-dashed) { animation: link-flow 4s linear infinite; stroke-dasharray: 6 4; }
:deep(g line.link-solid) { stroke-dasharray: none; }
@keyframes link-flow {
  to { stroke-dashoffset: -20; }
}

/* 选中节点发光增强 */
:deep(.selected-ring[stroke-opacity="0.4"]) {
  animation: glow-ring 2s ease-in-out infinite;
}
@keyframes glow-ring {
  0%, 100% { r: 22; stroke-opacity: 0.3; }
  50% { r: 26; stroke-opacity: 0.6; }
}

.kg-legend {
  position: absolute; bottom: var(--space-md); left: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  display: flex; flex-direction: column; gap: 6px;
  font-size: var(--text-xs);
}
.legend-row { display: flex; align-items: center; gap: var(--space-sm); flex-wrap: wrap; }
.legend-label { color: var(--text-muted); margin-right: 4px; }
.legend-chip { display: flex; align-items: center; gap: 4px; color: var(--text-secondary); cursor: pointer; padding: 2px 6px; border-radius: var(--radius-sm); transition: color var(--ease-out), background var(--ease-out); user-select: none; }
.legend-chip:hover { background: rgba(255,255,255,0.06); color: var(--text-primary); }
.legend-chip.active { color: #fff; background: rgba(255,255,255,0.12); }
.legend-chip i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.legend-row .legend-seal { width: 10px; height: 10px; border: 1px solid #e8453c; border-radius: 2px; background: transparent; }
.legend-row .legend-dash { width: 14px; height: 2px; border-top: 2px dashed rgba(255,255,255,0.5); background: transparent; border-radius: 0; }
.legend-row:last-child .legend-chip i { width: 14px; height: 2px; border-radius: 1px; }
</style>
