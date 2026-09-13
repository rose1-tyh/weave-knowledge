# 开发指南

> 面向后续迭代（自己或贡献者）：环境、命令、扩展任务的改动清单、工程纪律。

## 环境与常用命令

依赖：Python 3.11+ / Node 18+（开发机为 3.14 / 24）

```bash
# 后端
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --port 8000        # 开发服务（:8000）
python -m pytest tests/ -q                    # 全量测试（90+）
python -m ruff check backend                  # Lint（仓库根目录执行）

# 前端
cd frontend
npm install
npm run dev                                   # Vite :3000，/api 代理至 8000
npm test                                      # Vitest（56+）
npm run build                                 # 产物 → frontend/dist（后端托管）

# 桌面版（Windows）
cd backend && python scripts/make_icon.py     # 改品牌视觉后重新生成图标
build.bat                                     # npm build + PyInstaller → dist/织识/织识.exe
python run.py --browser                       # 浏览器模式启动（默认原生窗口）

# 演示数据
cd backend && python scripts/seed_demo.py     # 离线幂等，--force 重灌
```

## 架构导览（改一处要动哪些文件）

```
请求 → routers/<域>.py → services/<能力>_service.py → database.py(SQLite)
前端 → api/index.js(axios 统一封装) → stores/(pinia) → views/ + components/
```

- **领域色板/标签**：后端 `services/domain_constants.py` ↔ 前端 `src/design/tokens.js`，两处必须同步改
- **主题**：所有颜色用 `styles/variables.css` 的 CSS 变量；D3/SVG 属性用 `cssVar()` 运行时取值；禁止硬编码色值
- **提取管线**：`services/extraction_service.py`（阶段/进度）+ `services/ai_service.py`（LLM 调用与分片）；新增阶段需同步 `STAGE_PROGRESS` 与前端 `STAGE_LABELS`
- **数据库迁移**：`database.py` 的 `MIGRATIONS` 字典（幂等 ALTER），新表写进 `init_db` 的 DDL

## 常见扩展任务

### 新增概念类型（如 experiment）
1. `backend/services/domain_constants.py`：`TYPE_COLORS` / `TYPE_LABELS` 加条目
2. `frontend/src/design/tokens.js`：`TYPE_META`（及 `TYPE_SHORT`）加同名条目
3. `backend/services/ai_service.py`：提取 prompt 的 type 枚举说明中补充
4. 测试：`test_analytics_export.py` 的类型构成用例顺手补一条

### 新增关系类型
同上，改 `REL_COLORS` / `REL_LABELS` / `REL_META` 与 prompt 枚举。

### 新增 API
1. 按领域放进对应 `routers/*.py`（新领域则新建 router 并在 `main.py` 挂载）
2. 业务逻辑写进 service；数据库操作不进路由层
3. `tests/` 补对应测试（conftest 的 `db` fixture 提供隔离 SQLite）
4. 前端 `api/index.js` 加调用函数

### 新增前端页面
1. `views/` 新建组件；`router/index.js` 加路由（`meta.title` + `meta.transition`）
2. 顶部导航 / 命令面板动作项按需加入
3. 图表数据变换写成 `utils/` 纯函数并测试（参考 `charts.js`）

### 改 AI 配置面（BYOK）
- 存储：`services/settings_service.py` 的 `_FIELDS`（key → env 出厂默认）；路由 `routers/settings.py`（掩码/校验）
- 消费：`AIService.for_settings()` / `EmbeddingService.for_settings()`——新消费点一律按设置实例化，禁止 import 期固化
- 前端预设：`design/providerPresets.js`（预设=填表快捷方式，协议只有 openai/anthropic 二分）
- `app_settings.scope` 为多用户预留位，将来按 user_id 隔离无需改表

### 新增导出格式
`backend/services/export_service.py` 加方法 + `routers/graph.py` 加端点；
二进制格式用 `Response(content=..., media_type=..., Content-Disposition)` 参照 Anki 导出。

## 工程纪律

- **测试先行**：每个功能点带测试；提交前 `pytest` + `npm test` 全绿 + `ruff check backend` 通过（CI 会跑同样的三件套）
- **提交规范**：中文 conventional commits——`feat(域): 摘要——要点列表`，一个逻辑变更一个提交
- **版本发布**：`config.py APP_VERSION` / `frontend/package.json version` / `CHANGELOG.md` 三处同步 → 提交 → `git tag -a vX.Y.Z` → 推送 tag 触发 `release.yml` 自动构建 Windows 安装包并挂到 GitHub Release
- **安全底线**：`.env` / `storage/` / 密钥永不入库；用户输入渲染先转义（参考 `renderSnippet`）；对外抓取走 `_validate_public_url`

## 已知边界（迭代时留意）

- 单进程 SQLite：任务表不支持多 worker；向量检索为内存余弦扫描（万级概念内够用）
- 手动增删概念不重建向量索引（提取时自动索引），可调 `POST /api/system/reindex-embeddings` 修复
- URL 抓取存在 DNS rebinding 理论窗口（`routers/extract.py` docstring 有标注）
- 桌面窗口依赖 WebView2（Win10/11 一般自带）；缺失时 run.py 自动回退浏览器模式
