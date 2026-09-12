<template>
  <div class="app-shell">
    <GlowCursor />
    <AppHeader />
    <main class="app-main">
      <router-view v-slot="{ Component, route }">
        <transition :name="route.meta.transition || 'fade-slide'" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>
    <!-- 全局命令面板（⌘K / Ctrl+K，所有页面可用） -->
    <CommandPalette :open="paletteOpen" @close="paletteOpen = false" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import GlowCursor from '@/components/motion/GlowCursor.vue'
import CommandPalette from '@/components/CommandPalette.vue'

const paletteOpen = ref(false)

function onKeydown(e) {
  if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K' || e.code === 'KeyK')) {
    e.preventDefault()
    paletteOpen.value = !paletteOpen.value
  } else if (e.key === 'Escape' && paletteOpen.value) {
    paletteOpen.value = false
  }
}
// AppHeader 搜索按钮入口
function onOpenPalette() {
  paletteOpen.value = true
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('weave:open-cmdk', onOpenPalette)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('weave:open-cmdk', onOpenPalette)
})
</script>

<style>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--space-deep);
}
.app-main {
  flex: 1;
  overflow: hidden;
}
</style>
