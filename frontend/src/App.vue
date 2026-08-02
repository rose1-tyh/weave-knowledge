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
  </div>
</template>

<script setup>
import AppHeader from '@/components/AppHeader.vue'
import GlowCursor from '@/components/motion/GlowCursor.vue'
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
