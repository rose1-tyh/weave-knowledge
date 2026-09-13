# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循语义化版本（SemVer）。

## [3.2.0] — 2026-09-13

桌面应用化与 GitHub 分享就绪。

### 新增
- **桌面原生窗口**：run.py 经 pywebview（WebView2）打开独立应用窗口，替代「自动开浏览器」；WebView2 缺失或 `--browser`/`WEAVE_UI=browser` 时自动回退浏览器模式（三级兜底）
- **应用图标**：朱砂「织」多尺寸 ico（任务栏/exe/窗口）+ 512px PNG（`scripts/make_icon.py` 可重新生成）
- **记住上次页面**：桌面模式（`/api/health` 的 appMode 标记）下启动自动恢复上次浏览的页面；浏览器模式行为不变
- **单实例锁跨平台**：Windows msvcrt / POSIX fcntl 自动适配
- **发布流水线**：`release.yml`——推送 `v*` 标签自动构建 Windows 桌面包并挂到 GitHub Release
- **开发指南** `docs/DEVELOPMENT.md`：扩展任务改动清单（加类型/加 API/加页面/加导出）+ 工程纪律 + 发布流程
- Dependabot（pip / npm / github-actions 周更）

### 变更
- 版本单一来源 `config.APP_VERSION`（3.2.0），`/api/health` 返回 version + appMode；前端 package.json 版本同步

## [3.1.0] — 2026-09-12

竞赛级全面升级：提取管线重构、混合检索、知识洞察、双主题设计系统与工程化补全。

### 新增（后端）
- **提取管线 v2**：`extract_tasks` 任务持久化表，queued→parsing→chunking→extracting(i/n)→scoring→graphing 分阶段真实进度；SSE 端点 `GET /api/extract/progress/{paper_id}` 实时推送 + 15s 心跳 + 终态自关闭；`POST /api/extract/{paper_id}/retry` 失败重试；启动时自动恢复遗留任务
- **混合检索**：`GET /api/search` 三通道召回（概念 FTS5 BM25 + 论文正文全文 + embedding 语义向量）经 Reciprocal Rank Fusion 融合排序，snippet 高亮 + 分页；正文入 `papers_fts` 索引，概念向量入 `concept_embeddings`（未配置 embedding 自动降级）
- **知识洞察**：`GET /api/analytics/overview` —— 概念/关系类型构成、纯 Python PageRank 核心概念 TopN（跨论文同名聚合）、跨论文概念重合度；全库/单篇双 scope
- **Anki 导出**：`GET /api/export/{paper_id}/anki` 生成 .apkg 卡片包（genanki，牌组 ID 稳定幂等）
- **演示数据**：`python scripts/seed_demo.py` 一键灌入 3 篇示例论文（离线、幂等）

### 新增（前端）
- **墨夜/宣纸双主题**：`html.light` 宣纸亮色主题 + `useTheme` composable（localStorage 持久化 + 跟随系统）；D3 图谱 SVG 经 `cssVar()` 运行时取主题色
- **全局命令面板**：⌘K/Ctrl+K 呼出（全页面可用），混合检索分组结果 + 高亮 + 内置导航动作 + 键盘导航
- **SSE 实时进度 UI**：织网动画由真实任务阶段驱动（分片明细 + 百分比），失败面板含错误信息与重试
- **Markdown 编辑器**：概念定义双栏编辑 + 实时预览（markdown-it，html 关闭防 XSS），图谱 tooltip/导出适配
- **知识洞察页** `/analytics`：手写 SVG 图表（类型环图/关系条形/PageRank TopN/跨论文重合），零图表库依赖
- **审校乐观更新**：确认/驳回即时生效（失败回滚），替代整图 reload；导出 PNG 背景随主题

### 变更
- 后端路由按领域拆分：knowledge.py（506 行）→ extract / graph / library / explore / system 五个 router
- CORS 收紧为 localhost 正则白名单；`/api/extract-url` 增加 SSRF 防护（scheme 白名单 + 私网/环回 DNS 拦截 + 响应体 5MB 截断）
- 统一日志体系：滚动文件 + RequestID 中间件（X-Request-ID 透传 + 访问日志 + 异常落盘）
- 接口契约收紧：裸 dict 入参补 Pydantic 模型、DELETE/UPDATE 补 404/409 语义、关系创建校验两端概念存在
- 领域色板/标签单一来源：后端 `services/domain_constants.py`、前端 `src/design/tokens.js`
- 启动时 FTS 索引改为按需重建（计数失同步才 rebuild）；merge 建议复用落库向量，消除 O(N²) 请求时 HTTP 调用
- AI 调用与文档解析全部经 `asyncio.to_thread` 执行，提取期间事件循环不再阻塞

### 工程化
- 根 `pyproject.toml`（ruff + coverage 配置）；requirements 增 genanki / ruff / pytest-cov
- GitHub Actions CI：后端 ruff + pytest（覆盖率）、前端 vitest + build
- Docker：多阶段 Dockerfile + docker-compose（数据卷持久化，AI Key 经环境变量注入）
- 补 LICENSE（MIT）、CHANGELOG；README 全面重写（架构图/功能矩阵/技术亮点）

### 测试
- 后端 48 → 90（进度持久化/SSE 流/混合检索/RRF/PageRank/Anki/SSRF/中间件等）
- 前端 41 → 56（主题切换/SSE composable/Markdown 安全/图表几何/命令面板等）

## [3.0.0] — 2026-08-02

- v3.0 视觉门面：设计令牌体系、动效组件库（CountUp/SkeletonBlock/RevealOnScroll/GlowCursor/SealBadge）、路由转场、五页面重构
- 图谱交互增强：搜索定位/图例过滤/框选多选/拖拽建关系
- 可信抽取：原文证据定位、AI×文本信号交叉置信度、确认/驳回工作流、印章视觉
- 性能优化：FTS5 trigram 全文搜索、AI 提取异步化轮询、D3 增量渲染、列表排除大字段
- 桌面打包：PyInstaller onedir + 单实例锁 + 端口探测 + 数据目录抽象（WEAVE_DATA_DIR）

## [2.0.0] — 2026-08-02

- 初始开源版本：PDF/DOCX 上传、AI 概念/关系提取、D3 力导向图谱、跨论文融合、导入向导
