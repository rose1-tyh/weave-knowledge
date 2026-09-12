<template>
  <header class="app-header glass-panel">
    <!-- Logo -->
    <router-link to="/" class="logo">
      <span class="logo-mark">织</span>
      <span class="logo-text">织识</span>
    </router-link>

    <!-- 主导航 -->
    <nav class="main-nav">
      <router-link to="/" class="nav-item" exact-active-class="active">
        <el-icon class="nav-icon"><HomeFilled /></el-icon>首页
      </router-link>
      <router-link to="/library" class="nav-item" active-class="active">
        <el-icon class="nav-icon"><Collection /></el-icon>知识库
      </router-link>
      <router-link to="/explore" class="nav-item" active-class="active">
        <el-icon class="nav-icon"><Connection /></el-icon>全局探索
      </router-link>
    </nav>

    <!-- 右侧：搜索 / 主题切换 / 上传 -->
    <div class="header-actions">
      <button class="btn-cmdk" title="全局搜索（Ctrl+K）" @click="openPalette">
        <el-icon><Search /></el-icon><span class="kbd-hint">Ctrl K</span>
      </button>
      <button
        class="btn-theme"
        :title="theme === 'dark' ? '切换到宣纸主题' : '切换到墨夜主题'"
        data-test="theme-toggle"
        @click="toggleTheme"
      >
        <el-icon><Moon v-if="theme === 'dark'" /><Sunny v-else /></el-icon>
      </button>
      <button class="btn-upload" @click="router.push('/import')">
        <el-icon class="btn-icon"><Plus /></el-icon>上传论文
      </button>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { HomeFilled, Collection, Connection, Search, Moon, Sunny, Plus } from '@element-plus/icons-vue'
import { useTheme } from '@/composables/useTheme'

const router = useRouter()
const { theme, toggleTheme } = useTheme()

function openPalette() {
  window.dispatchEvent(new CustomEvent('weave:open-cmdk'))
}
</script>

<style scoped>
.app-header {
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 var(--space-lg);
  gap: var(--space-xl);
  flex-shrink: 0;
  z-index: 100;
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  text-decoration: none;
  flex-shrink: 0;
}
.logo-mark {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--vermilion);
  color: #fff;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  border-radius: var(--radius-sm);
  box-shadow: var(--vermilion-glow);
}
.logo-text {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.03em;
}

/* 主导航 */
.main-nav {
  display: flex;
  gap: var(--space-xs);
  flex: 1;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: 500;
  transition: all var(--ease-out);
}
.nav-item:hover {
  color: var(--text-primary);
  background: var(--hover-tint);
}
.nav-item.active {
  color: var(--vermilion);
  background: var(--vermilion-bg);
}
.nav-icon {
  font-size: 14px;
}

/* 右侧动作区 */
.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

/* 全局搜索入口 */
.btn-cmdk {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--space-surface);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-family: inherit;
  cursor: pointer;
  transition: all var(--ease-out);
}
.btn-cmdk:hover { color: var(--cyan); border-color: var(--cyan); }
.kbd-hint {
  font-family: var(--font-mono);
  font-size: 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 3px;
  padding: 0 4px;
  color: var(--text-muted);
}

/* 主题切换 */
.btn-theme {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--space-surface);
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  transition: all var(--ease-out);
}
.btn-theme:hover {
  color: var(--amber);
  border-color: var(--amber);
  transform: translateY(-1px);
}

/* 上传按钮 */
.btn-upload {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border: 1px solid var(--vermilion);
  border-radius: var(--radius-md);
  background: var(--vermilion-bg);
  color: var(--vermilion);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--ease-out);
  font-family: inherit;
}
.btn-upload:hover {
  background: var(--vermilion);
  color: #fff;
  box-shadow: var(--vermilion-glow);
}
.btn-icon {
  font-size: 14px;
}
</style>
