<template>
  <div class="settings-page">
    <header class="set-head">
      <div>
        <h2 class="set-title">设置</h2>
        <p class="set-sub">自带 API Key（BYOK）—— Key 仅保存在本机，不会上传到任何服务器</p>
      </div>
    </header>

    <!-- 模型服务 -->
    <section class="set-card glass-panel">
      <h3>模型服务 <span class="set-cap">AI 提取使用的大语言模型</span></h3>

      <div class="preset-grid">
        <button v-for="p in presets" :key="p.id" class="preset-card"
          :class="{ active: selectedPreset === p.id }" @click="applyPreset(p)">
          <span class="pc-label">{{ p.label }}</span>
          <span v-if="p.note" class="pc-note">{{ p.note }}</span>
        </button>
      </div>

      <div class="form-grid">
        <label>API Key <span class="req">*</span></label>
        <div class="key-row">
          <input v-model="form.apiKey" class="set-input" :type="showKey ? 'text' : 'password'"
            data-test="api-key-input" :placeholder="hasKey ? `已保存：${apiKeyMasked}（不修改则留空）` : 'sk-…'"
            autocomplete="off" @input="keyDirty = true" />
          <button class="mini-btn" type="button" @click="showKey = !showKey">{{ showKey ? '隐藏' : '显示' }}</button>
        </div>

        <label>模型名称</label>
        <div class="key-row">
          <input v-model="form.aiModel" class="set-input" list="model-suggestions"
            placeholder="如 deepseek-chat" />
          <datalist id="model-suggestions">
            <option v-for="m in activePreset?.models || []" :key="m" :value="m" />
          </datalist>
        </div>

        <template v-if="selectedPreset === 'custom' || form.baseUrl">
          <label>Base URL</label>
          <input v-model="form.baseUrl" class="set-input" placeholder="https://…（OpenAI 兼容端点）" />
        </template>
        <template v-else>
          <label>Base URL</label>
          <input v-model="form.baseUrl" class="set-input" placeholder="由预设自动填写" />
        </template>
      </div>
      <p v-if="activePreset?.keySite" class="key-hint">
        Key 获取：<code>{{ activePreset.keySite }}</code> · 模型名可自由填写，预设仅供快捷选择
      </p>
    </section>

    <!-- 语义检索（可选） -->
    <section class="set-card glass-panel">
      <h3>语义检索 <span class="set-cap">可选 · 未配置时自动降级为关键词检索</span></h3>
      <div class="form-grid">
        <label>Embedding Base URL</label>
        <input v-model="form.embeddingBaseUrl" class="set-input"
          placeholder="如 https://api.siliconflow.cn/v1（留空关闭）" />
        <label>Embedding Key</label>
        <input v-model="form.embeddingApiKey" class="set-input" type="password" autocomplete="off"
          :placeholder="hasEmbedding ? `已保存：${embeddingApiKeyMasked}（不修改则留空）` : '选填'" />
        <label>Embedding 模型</label>
        <input v-model="form.embeddingModel" class="set-input" placeholder="如 BAAI/bge-m3" />
      </div>
      <button class="mini-btn emb-quick" type="button" @click="applySiliconflowEmbedding">
        一键填入硅基流动 bge-m3
      </button>
    </section>

    <!-- 操作区 -->
    <section class="set-actions glass-panel">
      <el-button type="primary" data-test="save-settings" :loading="saving" @click="save">保存设置</el-button>
      <el-button data-test="test-settings" :loading="testing" @click="test">测试连接</el-button>
      <span v-if="testResult" class="test-result" :class="testResult.ok ? 'ok' : 'fail'" data-test="test-result">
        {{ testResult.ok ? `连接正常 · ${testResult.latencyMs}ms` : `连接失败：${testResult.error}` }}
      </span>
      <Transition name="set-fade">
        <span v-if="savedTip" class="saved-tip">已保存 ✓</span>
      </Transition>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSettings, testSettings } from '@/api'
import { useApiError } from '@/composables/useApiError'
import { PROVIDER_PRESETS, matchPreset } from '@/design/providerPresets'

const { showError } = useApiError()
const presets = PROVIDER_PRESETS

const selectedPreset = ref('deepseek')
const form = ref({
  apiKey: '', aiModel: '', baseUrl: '',
  embeddingBaseUrl: '', embeddingApiKey: '', embeddingModel: '',
})
const apiKeyMasked = ref('')
const embeddingApiKeyMasked = ref('')
const hasKey = ref(false)
const hasEmbedding = ref(false)
const showKey = ref(false)
const keyDirty = ref(false)
const embeddingKeyDirty = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)
const savedTip = ref(false)

const activePreset = computed(() => presets.find(p => p.id === selectedPreset.value))

function applyPreset(p) {
  selectedPreset.value = p.id
  form.value.baseUrl = p.baseUrl
  if (p.models.length) form.value.aiModel = p.models[0]
  if (p.embedding && !form.value.embeddingBaseUrl) {
    form.value.embeddingBaseUrl = p.embedding.baseUrl
    form.value.embeddingModel = p.embedding.model
  }
}

function applySiliconflowEmbedding() {
  form.value.embeddingBaseUrl = 'https://api.siliconflow.cn/v1'
  form.value.embeddingModel = 'BAAI/bge-m3'
}

onMounted(async () => {
  try {
    const s = await getSettings()
    apiKeyMasked.value = s.apiKeyMasked
    embeddingApiKeyMasked.value = s.embeddingApiKeyMasked
    hasKey.value = s.hasKey
    hasEmbedding.value = s.hasEmbedding
    form.value.aiModel = s.aiModel || ''
    form.value.baseUrl = s.aiBaseUrl || ''
    form.value.embeddingBaseUrl = s.embeddingBaseUrl || ''
    form.value.embeddingModel = s.embeddingModel || ''
    selectedPreset.value = matchPreset(s.aiBaseUrl, s.aiProvider)
  } catch (e) {
    showError(e, '设置加载失败')
  }
})

async function save() {
  saving.value = true
  try {
    const payload = {
      ai_provider: activePreset.value.provider,
      ai_base_url: form.value.baseUrl.trim(),
      ai_model: form.value.aiModel.trim(),
      ai_embedding_base_url: form.value.embeddingBaseUrl.trim() || '',
      ai_embedding_model: form.value.embeddingModel.trim() || '',
    }
    // Key 仅在用户实际输入时提交（掩码回显不覆盖）
    if (keyDirty.value && form.value.apiKey.trim()) payload.ai_api_key = form.value.apiKey.trim()
    if (embeddingKeyDirty.value && form.value.embeddingApiKey.trim()) payload.ai_embedding_api_key = form.value.embeddingApiKey.trim()

    const s = await updateSettings(payload)
    hasKey.value = s.hasKey
    hasEmbedding.value = s.hasEmbedding
    apiKeyMasked.value = s.apiKeyMasked
    embeddingApiKeyMasked.value = s.embeddingApiKeyMasked
    form.value.apiKey = ''
    form.value.embeddingApiKey = ''
    keyDirty.value = false
    embeddingKeyDirty.value = false
    savedTip.value = true
    setTimeout(() => { savedTip.value = false }, 2000)
  } catch (e) {
    showError(e, '保存失败')
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  testResult.value = null
  try {
    const payload = {
      ai_provider: activePreset.value.provider,
      ai_base_url: form.value.baseUrl.trim() || undefined,
      ai_model: form.value.aiModel.trim() || undefined,
    }
    if (keyDirty.value && form.value.apiKey.trim()) payload.ai_api_key = form.value.apiKey.trim()
    testResult.value = await testSettings(payload)
  } catch (e) {
    showError(e, '测试失败')
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.settings-page {
  position: relative;
  height: 100%;
  overflow-y: auto;
  padding: var(--space-lg) var(--space-xl) var(--space-2xl);
  background: var(--space-deep);
}
.set-head { margin-bottom: var(--space-lg); }
.set-title { font-family: var(--font-display); font-size: var(--text-2xl); color: var(--text-primary); }
.set-sub { font-size: var(--text-sm); color: var(--text-muted); margin-top: 4px; }

.set-card { padding: var(--space-lg); background: var(--space-surface); margin-bottom: var(--space-lg); }
.set-card h3 { font-family: var(--font-display); font-size: var(--text-md); color: var(--text-primary); margin-bottom: var(--space-md); }
.set-cap { font-family: var(--font-body); font-size: var(--text-xs); font-weight: 400; color: var(--text-muted); margin-left: var(--space-sm); }

/* 预设卡片 */
.preset-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--space-sm); margin-bottom: var(--space-lg); }
.preset-card {
  display: flex; flex-direction: column; gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--space-surface);
  color: var(--text-secondary);
  text-align: left;
  cursor: pointer;
  transition: all var(--ease-out);
  font-family: inherit;
}
.preset-card:hover { border-color: var(--vermilion); color: var(--text-primary); transform: translateY(-1px); }
.preset-card.active { border-color: var(--vermilion); background: var(--vermilion-bg); color: var(--vermilion); box-shadow: var(--vermilion-glow); }
.pc-label { font-size: var(--text-sm); font-weight: 600; }
.pc-note { font-size: var(--text-xs); color: var(--text-muted); }

/* 表单 */
.form-grid { display: grid; grid-template-columns: 140px 1fr; gap: 12px var(--space-md); align-items: center; max-width: 720px; }
.form-grid label { font-size: var(--text-sm); color: var(--text-secondary); text-align: right; }
.req { color: var(--vermilion); }
.set-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--space-surface);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  outline: none;
  transition: border-color var(--ease-out);
}
.set-input:focus { border-color: var(--vermilion); }
.key-row { display: flex; gap: var(--space-sm); }
.key-row .set-input { flex: 1; }
.key-hint { margin-top: var(--space-md); font-size: var(--text-xs); color: var(--text-muted); }
.key-hint code { font-family: var(--font-mono); color: var(--cyan); }
.mini-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  cursor: pointer;
  font-family: inherit;
  transition: all var(--ease-out);
}
.mini-btn:hover { color: var(--vermilion); border-color: var(--vermilion); }
.emb-quick { margin-top: var(--space-md); }

/* 操作区 */
.set-actions { display: flex; align-items: center; gap: var(--space-md); padding: var(--space-md) var(--space-lg); }
.test-result { font-size: var(--text-sm); }
.test-result.ok { color: var(--emerald); }
.test-result.fail { color: var(--vermilion); max-width: 520px; overflow-wrap: anywhere; }
.saved-tip { color: var(--emerald); font-size: var(--text-sm); }
.set-fade-enter-active, .set-fade-leave-active { transition: opacity var(--ease-out); }
.set-fade-enter-from, .set-fade-leave-to { opacity: 0; }
</style>
