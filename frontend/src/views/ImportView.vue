<template>
  <div class="import-page">
    <div class="import-container">
      <h1 class="import-title">导入知识</h1>
      <p class="import-subtitle">四步选择一种方式，将文献织入你的知识网络</p>
      <ImportWizard />
    </div>
  </div>
</template>

<script setup>
import ImportWizard from '@/components/ImportWizard.vue'
</script>

<style scoped>
.import-page {
  --page-accent: var(--page-home-accent);
  height: 100%;
  overflow-y: auto;
  padding: var(--space-xl) var(--space-2xl);
  background:
    radial-gradient(ellipse 60% 45% at 18% 12%, rgba(232, 69, 60, 0.16) 0%, transparent 62%),
    radial-gradient(ellipse 60% 45% at 82% 88%, rgba(0, 212, 255, 0.12) 0%, transparent 62%),
    radial-gradient(ellipse 40% 30% at 75% 20%, rgba(232, 69, 60, 0.06) 0%, transparent 60%),
    var(--space-deep);
}

.import-container {
  max-width: 640px;
  margin: 0 auto;
  padding-top: var(--space-lg);
}

.import-title {
  font-family: var(--font-display);
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--text-primary);
  text-align: center;
  letter-spacing: 0.12em;
  text-shadow: 0 0 24px rgba(232, 69, 60, 0.35);
}

.import-subtitle {
  font-size: var(--text-base);
  color: var(--text-muted);
  text-align: center;
  margin-top: var(--space-sm);
  margin-bottom: var(--space-2xl);
  letter-spacing: 0.04em;
}
</style>
