/**
 * 主题切换 —— 墨夜（dark，默认）/ 宣纸（light）
 *
 * 持久化于 localStorage（weave-theme），首次访问跟随系统 prefers-color-scheme；
 * 通过在 <html> 上切换 .light 类驱动 variables.css 的双主题令牌。
 */
import { ref, watchEffect } from 'vue'

const THEME_KEY = 'weave-theme'

function initialTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* localStorage 不可用时跟随系统 */ }
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

const theme = ref(initialTheme())

watchEffect(() => {
  document.documentElement.classList.toggle('light', theme.value === 'light')
  try { localStorage.setItem(THEME_KEY, theme.value) } catch { /* 忽略 */ }
})

export function useTheme() {
  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }
  return { theme, toggleTheme }
}
