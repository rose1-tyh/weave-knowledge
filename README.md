# 织识 — 学术知识重构引擎

> 创意大赛 · 知识重构赛道参赛作品

**织识** 是一个 AI 驱动的学术知识重构工具。上传论文 PDF，AI 自动提取核心概念及其关系，构建交互式知识图谱——让散落的文献编织成网。

区别于市面 ChatPDF 类产品：**织识不做对话问答，而是重构知识结构**。

---

## 功能

1. **PDF 上传解析** — 上传学术论文 PDF，自动提取全文并分页
2. **AI 知识提取** — Claude 识别核心概念（方法/理论/数据集/发现/工具）及其关系
3. **交互式知识图谱** — D3 力导向图展示概念网络，支持拖拽、缩放、点击查看详情
4. **概念详情面板** — 点击节点查看定义、类型、原文页码

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Element Plus + D3.js |
| 后端 | Python FastAPI |
| PDF 解析 | PyMuPDF |
| AI 引擎 | Claude API 或 DeepSeek（OpenAI 兼容，可切换） |
| 设计 | 朱砂红 + 墨色 + 宣纸（中国传统学术美学）|

## 快速开始

### 1. 后端

```bash
cd backend
pip install -r requirements.txt

# 配置 AI 提供方（二选一），复制 .env.example 为 .env 并填写：
#   DeepSeek（推荐，便宜）: AI_PROVIDER=openai + AI_API_KEY
#   Claude:               AI_PROVIDER=anthropic + ANTHROPIC_API_KEY
# 参考 backend/.env.example

uvicorn main:app --reload --port 8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

### 3. 使用

1. 浏览器打开 `http://localhost:3000`
2. 拖拽一篇学术论文 PDF 到上传区域
3. 等待 AI 提取（约 10-30 秒）
4. 在知识图谱中浏览概念及其关系

## 项目结构

```
E:\知识重构\
├── frontend/                  # Vue 3 前端
│   └── src/
│       ├── views/
│       │   ├── HomeView.vue       # 首页（品牌 + 上传）
│       │   └── GraphView.vue      # 图谱页
│       ├── components/
│       │   ├── KnowledgeGraph.vue # D3 力导向知识图谱
│       │   ├── ConceptCard.vue    # 概念详情卡片
│       │   ├── UploadPanel.vue    # 拖拽上传面板
│       │   └── AppHeader.vue      # 导航栏
│       ├── api/index.js           # API 封装
│       └── styles/
│           ├── variables.css      # 设计令牌
│           └── global.css         # 全局样式
├── backend/                   # Python FastAPI 后端
│   ├── main.py                    # 应用入口
│   ├── config.py                  # 配置
│   ├── routers/
│   │   ├── upload.py              # PDF 上传 + 解析 API
│   │   └── knowledge.py           # AI 提取 + 图谱 API
│   ├── services/
│   │   ├── pdf_service.py         # PyMuPDF 文本提取
│   │   ├── ai_service.py          # Claude API 调用
│   │   └── graph_service.py       # 图谱数据构建
│   └── models/schemas.py          # Pydantic 数据模型
└── README.md
```

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/upload` | 上传 PDF，返回论文信息 |
| POST | `/api/extract` | AI 知识提取，返回图谱数据 |
| GET | `/api/paper/{id}` | 获取论文基本信息 |
| GET | `/api/health` | 健康检查 |

统一响应格式：`{ code: 200, msg: "操作成功", data: {...} }`

## License

MIT
