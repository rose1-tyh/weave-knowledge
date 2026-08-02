"""AI 知识提取服务 —— 支持 Claude（Anthropic SDK）与 DeepSeek 等 OpenAI 兼容接口"""

import json
import re
import requests
from config import AI_API_KEY, AI_MODEL, AI_PROVIDER, AI_BASE_URL, MAX_CHUNK_CHARS

KNOWLEDGE_EXTRACTION_PROMPT = """你是一个学术知识提取引擎。阅读以下论文内容，完成知识提取。

## 任务
1. **提取核心概念**（5-10个）：每个概念包含：
   - name: 概念名称（简洁，2-8字）
   - definition: 一句话定义（清晰阐述该概念在论文中的含义）
   - type: 概念类型，从以下选择：method（研究方法）、theory（理论基础）、dataset（数据集）、finding（研究发现）、tool（工具/系统）
   - page: 该概念在原文中首次出现或核心论述所在的页码

2. **提取概念间关系**：
   - source: 源概念名称（必须与上面提取的 name 完全一致）
   - target: 目标概念名称（必须与上面提取的 name 完全一致）
   - type: 关系类型，从以下选择：supports（A支撑/验证B）、contradicts（A与B矛盾/质疑）、extends（A扩展/改进B）、cites（A引用B）、uses（A使用B作为方法/工具）
   - evidence: 原文中体现该关系的具体语句（直接引用）

## 输出格式
严格按以下 JSON 格式输出，不要包含任何其他文字、注释或 Markdown 标记：

{
  "concepts": [
    {"name": "...", "definition": "...", "type": "...", "page": 1}
  ],
  "relations": [
    {"source": "...", "target": "...", "type": "...", "evidence": "..."}
  ]
}"""


class AIService:
    """AI 知识提取：按提供方调用（anthropic / openai 兼容），处理分片与合并"""

    def __init__(self):
        self.provider = AI_PROVIDER
        self.model = AI_MODEL
        self.api_key = AI_API_KEY
        self.base_url = AI_BASE_URL.rstrip("/")
        if self.provider == "anthropic":
            from anthropic import Anthropic
            self._anthropic = Anthropic(api_key=self.api_key)
        else:
            self._anthropic = None

    def extract_knowledge(self, full_text: str, paper_title: str) -> dict:
        """从论文全文中提取知识图谱"""
        # 长文本分片
        if len(full_text) <= MAX_CHUNK_CHARS:
            return self._extract_single(full_text, paper_title)

        # 分片提取
        chunks = self._chunk_text(full_text)
        all_concepts = {}
        all_relations = []

        for i, chunk in enumerate(chunks):
            chunk_label = f"{paper_title}（第{i+1}/{len(chunks)}段）"
            result = self._extract_single(chunk, chunk_label)
            for c in result.get("concepts", []):
                if c["name"] not in all_concepts:
                    all_concepts[c["name"]] = c
            all_relations.extend(result.get("relations", []))

        # 去重关系
        seen = set()
        unique_relations = []
        for r in all_relations:
            key = (r["source"], r["target"], r["type"])
            if key not in seen:
                seen.add(key)
                unique_relations.append(r)

        return {
            "concepts": list(all_concepts.values()),
            "relations": unique_relations,
        }

    def _chunk_text(self, text: str) -> list[str]:
        """按字符数切分文本，尽量在段落边界断开"""
        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < MAX_CHUNK_CHARS:
                current += para + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                current = para + "\n\n"
        if current.strip():
            chunks.append(current.strip())
        return chunks

    def _extract_single(self, text: str, title: str) -> dict:
        """按提供方调用 AI 提取单个文本片段的知识"""
        user_content = f"## 论文标题\n{title}\n\n## 论文内容\n{text}"

        if self.provider == "anthropic":
            response = self._anthropic.messages.create(
                model=self.model,
                max_tokens=4096,
                system=KNOWLEDGE_EXTRACTION_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            raw = response.content[0].text.strip()
        else:
            raw = self._call_openai_compat(KNOWLEDGE_EXTRACTION_PROMPT, user_content)

        return self._parse_json(raw)

    def _call_openai_compat(self, system_prompt: str, user_content: str) -> str:
        """调用 OpenAI 兼容接口（DeepSeek 等）"""
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 4096,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """从 Claude 回复中稳健解析 JSON"""
        # 移除可能的 Markdown 代码块包裹
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', raw)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 尝试提取 JSON 对象
            match = re.search(r'\{[\s\S]*\}', cleaned)
            if match:
                return json.loads(match.group())
            return {"concepts": [], "relations": []}
