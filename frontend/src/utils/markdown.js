/**
 * Markdown 渲染 —— 概念定义等富文本字段的统一渲染入口
 *
 * 安全策略：markdown-it 关闭 html 选项，用户输入中的 HTML 一律转义为纯文本，
 * 无需额外 sanitizer；链接默认 target=_blank + rel=noopener。
 */
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,        // 禁用内嵌 HTML（XSS 防线）
  linkify: true,
  breaks: true,       // 单换行 → <br>（贴合概念定义的书写习惯）
  typographer: true,
})

// 外链新窗口打开
const defaultLinkOpen = md.renderer.rules.link_open
  || ((tokens, idx, options, env, self) => self.renderToken(tokens, idx, options))
md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  tokens[idx].attrSet('target', '_blank')
  tokens[idx].attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen(tokens, idx, options, env, self)
}

/** Markdown → HTML（输入不可信，html 已禁用） */
export function renderMarkdown(text) {
  if (!text) return ''
  return md.render(String(text))
}

/** 纯文本摘要（列表/标题降为平文，供 tooltip / 单行展示） */
export function markdownPlain(text, maxLength = 120) {
  if (!text) return ''
  const plain = String(text)
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_~>#]+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  return plain.length > maxLength ? plain.slice(0, maxLength) + '…' : plain
}

/** 搜索高亮片段渲染：先转义 HTML，再还原服务端 <mark> 标记（内容安全） */
export function renderSnippet(snippet) {
  if (!snippet) return ''
  const esc = String(snippet)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return esc.replace(/&lt;mark&gt;/g, '<mark>').replace(/&lt;\/mark&gt;/g, '</mark>')
}
