/**
 * AI 提供方预设 —— BYOK 设置页的填表快捷方式
 *
 * 后端支持任意 OpenAI 兼容端点，预设只是「选卡片 → 自动填 base_url/推荐 model」；
 * 模型名迭代快，允许自由编辑。embedding 字段为该预设可选的语义检索配置。
 */

export const PROVIDER_PRESETS = [
  {
    id: 'deepseek',
    label: 'DeepSeek',
    provider: 'openai',
    baseUrl: 'https://api.deepseek.com',
    models: ['deepseek-chat', 'deepseek-reasoner'],
    keySite: 'platform.deepseek.com',
    note: '性价比高；暂无 embedding API',
  },
  {
    id: 'zhipu',
    label: '智谱 GLM',
    provider: 'openai',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    models: ['glm-4-flash', 'glm-4-air', 'glm-4-plus'],
    keySite: 'open.bigmodel.cn',
    note: 'glm-4-flash 免费档；有 embedding-3',
    embedding: { baseUrl: 'https://open.bigmodel.cn/api/paas/v4', model: 'embedding-3' },
  },
  {
    id: 'kimi',
    label: 'Kimi',
    provider: 'openai',
    baseUrl: 'https://api.moonshot.cn/v1',
    models: ['kimi-k2-turbo-preview', 'moonshot-v1-8k'],
    keySite: 'platform.moonshot.cn',
  },
  {
    id: 'qwen',
    label: '通义 Qwen',
    provider: 'openai',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: ['qwen-turbo', 'qwen-plus', 'qwen-max'],
    keySite: 'bailian.console.aliyun.com',
  },
  {
    id: 'siliconflow',
    label: '硅基流动',
    provider: 'openai',
    baseUrl: 'https://api.siliconflow.cn/v1',
    models: ['deepseek-ai/DeepSeek-V3', 'Qwen/Qwen2.5-72B-Instruct'],
    keySite: 'cloud.siliconflow.cn',
    note: '聚合平台；有 BAAI/bge-m3 embedding，可点亮语义检索',
    embedding: { baseUrl: 'https://api.siliconflow.cn/v1', model: 'BAAI/bge-m3' },
  },
  {
    id: 'anthropic',
    label: 'Claude',
    provider: 'anthropic',
    baseUrl: '',
    models: ['claude-sonnet-4-20250514'],
    keySite: 'console.anthropic.com',
    note: '官方 SDK 直连，无需 base_url',
  },
  {
    id: 'custom',
    label: '自定义',
    provider: 'openai',
    baseUrl: '',
    models: [],
    keySite: '',
    note: '任意 OpenAI 兼容端点（vLLM / OneAPI 等）',
  },
]

/** 按已保存的 base_url 猜测预设（用于回显选中态）；匹配不到 → custom */
export function matchPreset(baseUrl, provider) {
  if (provider === 'anthropic') return 'anthropic'
  const hit = PROVIDER_PRESETS.find(p => p.baseUrl && p.baseUrl === baseUrl)
  return hit ? hit.id : (baseUrl ? 'custom' : 'deepseek')
}
