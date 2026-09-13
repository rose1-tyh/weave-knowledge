import { describe, it, expect } from 'vitest'
import { PROVIDER_PRESETS, matchPreset } from '../providerPresets'

describe('PROVIDER_PRESETS', () => {
  it('覆盖全部国产模型预设 + Claude + 自定义', () => {
    const ids = PROVIDER_PRESETS.map(p => p.id)
    expect(ids).toEqual(expect.arrayContaining(['deepseek', 'zhipu', 'kimi', 'qwen', 'siliconflow', 'anthropic', 'custom']))
  })

  it('每个预设具备协议必要字段，baseUrl 均为 https', () => {
    for (const p of PROVIDER_PRESETS) {
      expect(['openai', 'anthropic']).toContain(p.provider)
      if (p.baseUrl) expect(p.baseUrl.startsWith('https://')).toBe(true)
      if (p.provider === 'openai' && p.id !== 'custom') expect(p.baseUrl).toBeTruthy()
    }
  })

  it('硅基流动/智谱附带 embedding 配置', () => {
    for (const id of ['siliconflow', 'zhipu']) {
      const p = PROVIDER_PRESETS.find(x => x.id === id)
      expect(p.embedding?.model).toBeTruthy()
    }
  })
})

describe('matchPreset', () => {
  it('按 base_url 精确匹配预设', () => {
    expect(matchPreset('https://api.deepseek.com', 'openai')).toBe('deepseek')
    expect(matchPreset('https://open.bigmodel.cn/api/paas/v4', 'openai')).toBe('zhipu')
  })

  it('anthropic 协议直接匹配 Claude', () => {
    expect(matchPreset('', 'anthropic')).toBe('anthropic')
  })

  it('未知端点 → custom；空端点默认 deepseek', () => {
    expect(matchPreset('https://my-llm.example/v1', 'openai')).toBe('custom')
    expect(matchPreset('', 'openai')).toBe('deepseek')
  })
})
