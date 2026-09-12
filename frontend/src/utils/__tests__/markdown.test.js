import { describe, it, expect } from 'vitest'
import { renderMarkdown, markdownPlain } from '../markdown'

describe('renderMarkdown', () => {
  it('基础语法渲染', () => {
    const html = renderMarkdown('**加粗** 与 `代码`')
    expect(html).toContain('<strong>加粗</strong>')
    expect(html).toContain('<code>代码</code>')
  })

  it('HTML 被转义（XSS 防线）', () => {
    const html = renderMarkdown('<img src=x onerror=alert(1)>**ok**')
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
    expect(html).toContain('<strong>ok</strong>')
  })

  it('链接带 target=_blank 与 noopener', () => {
    const html = renderMarkdown('[示例](https://example.com)')
    expect(html).toContain('target="_blank"')
    expect(html).toContain('rel="noopener noreferrer"')
  })

  it('空输入返回空串', () => {
    expect(renderMarkdown('')).toBe('')
    expect(renderMarkdown(null)).toBe('')
  })
})

describe('markdownPlain', () => {
  it('剥离语法为纯文本', () => {
    expect(markdownPlain('## 标题\n- **重点**内容')).toContain('标题')
    expect(markdownPlain('## 标题\n- **重点**内容')).toContain('重点内容')
    expect(markdownPlain('[链接文字](https://x.com)')).toBe('链接文字')
  })

  it('超长截断加省略号', () => {
    expect(markdownPlain('a'.repeat(200), 50)).toHaveLength(51)
    expect(markdownPlain('a'.repeat(200), 50).endsWith('…')).toBe(true)
  })
})
