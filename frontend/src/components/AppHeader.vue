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
        <span class="nav-icon">◆</span>首页
      </router-link>
      <router-link to="/library" class="nav-item" active-class="active">
        <span class="nav-icon">▣</span>知识库
      </router-link>
      <router-link to="/explore" class="nav-item" active-class="active">
        <span class="nav-icon">◎</span>全局探索
      </router-link>
    </nav>

    <!-- 右侧：上传按钮 -->
    <div class="header-actions">
      <button class="btn-upload" @click="$emit('upload')">
        <span class="btn-icon">+</span>上传论文
      </button>
    </div>
  </header>
</template>

<script setup>
defineEmits(['upload'])
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
  background: rgba(255,255,255,0.05);
}
.nav-item.active {
  color: var(--vermilion);
  background: var(--vermilion-bg);
}
.nav-icon {
  font-size: 10px;
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
  font-size: 16px;
  font-weight: 300;
}
</style>
