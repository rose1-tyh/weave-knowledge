<template>
  <div ref="container" class="kg-container">
    <div ref="tooltip" class="graph-tooltip"></div>
    <svg ref="svgEl"></svg>
    <!-- 图例 -->
    <div class="kg-legend glass-panel">
      <div class="legend-row">
        <span class="legend-label">概念</span>
        <span v-for="t in conceptTypes" :key="t.key" class="legend-chip">
          <i :style="{ background: t.color, boxShadow: `0 0 6px ${t.color}` }"></i>{{ t.label }}
        </span>
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

const props = defineProps({
  data: { type: Object, required: true },
  selectedId: { type: String, default: null },
  editing: Boolean,
})

const emit = defineEmits(['select-node', 'select-link', 'add-relation', 'edit-node'])

const container = ref(null)
const svgEl = ref(null)
const tooltip = ref(null)

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

onMounted(() => {
  render()
  resizeObserver = new ResizeObserver(() => render())
  resizeObserver.observe(container.value)
})
onUnmounted(() => {
  if (simulation) simulation.stop()
  if (resizeObserver) resizeObserver.disconnect()
})

watch(() => props.data, () => render())
watch(() => props.selectedId, (id) => highlightNode(id))

function render() {
  if (!container.value || !props.data) return
  // 重建前先停止旧力模拟，避免 d3-timer 持有旧引用持续 tick（侧栏折叠/转场会提高 render 频率）
  if (simulation) simulation.stop()

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
  zoomBehavior = d3.zoom().scaleExtent([0.15, 5]).on('zoom', e => {
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

  // 力模拟
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(140))
    .force('charge', d3.forceManyBody().strength(-500))
    .force('center', d3.forceCenter(0, 0))
    .force('collision', d3.forceCollide(50))

  // 边
  const linkG = g.append('g')
  const linkLines = linkG.selectAll('line').data(links).join('line')
    .attr('stroke', d => d.color || 'rgba(255,255,255,0.2)')
    .attr('stroke-opacity', 0.6)
    .attr('stroke-width', d => d.type === 'contradicts' ? 2 : 1.2)
    .attr('stroke-dasharray', d => d.type === 'contradicts' ? '8,4' : null)
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
    .attr('cursor', props.editing ? 'crosshair' : 'pointer')
    .call(d3.drag()
      .on('start', (e, d) => {
        if (props.editing) { dragSourceNode = d; return }
        if (!e.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
      })
      .on('drag', (e, d) => {
        if (props.editing) return
        d.fx = e.x; d.fy = e.y
      })
      .on('end', (e, d) => {
        if (props.editing && dragSourceNode && dragSourceNode !== d) {
          emit('add-relation', { source: dragSourceNode.id, target: d.id })
          dragSourceNode = null
          return
        }
        dragSourceNode = null
        if (!e.active) simulation.alphaTarget(0)
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
defineExpose({ zoomBy, resetZoom })
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

/* 节点脉冲动画 */
:deep(g g circle:nth-child(2)) {
  animation: node-pulse 3s ease-in-out infinite;
}
@keyframes node-pulse {
  0%, 100% { r: 18; }
  50% { r: 20; }
}

/* 连线流动动画 */
:deep(g line) {
  animation: link-flow 4s linear infinite;
  stroke-dasharray: 6 4;
}
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
.legend-chip { display: flex; align-items: center; gap: 4px; color: var(--text-secondary); }
.legend-chip i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.legend-row:last-child .legend-chip i { width: 14px; height: 2px; border-radius: 1px; }
</style>
