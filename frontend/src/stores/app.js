import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const globalLoading = ref(false)
  const loadingText = ref('')

  function setLoading(loading, text = '') {
    globalLoading.value = loading
    loadingText.value = text
  }

  return { globalLoading, loadingText, setLoading }
})
