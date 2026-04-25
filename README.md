# Persona

> 单用户、BYOK、约束式 AI 长篇创作平台

Persona 是一个面向长篇小说创作的本地优先工作台。它不追求“一键写小说”，而是把大模型放进一套可审阅、可挂载、可复用的创作约束系统里，让作者自己掌控 API Key、上下文资产和写作流程。

你可以先把已有文本样本分析成风格档案和情节档案，再把这些档案挂到具体项目上，在项目工作台整理设定与大纲，最后进入沉浸编辑器进行 AI 协作写作、续写、记忆同步与导出。

## 核心能力

- **BYOK Provider 配置中心**：统一维护 OpenAI-compatible 网关、默认模型与 API Key 掩码，支持测试连接。
- **Style Lab**：把单个 TXT 样本沉淀为分析报告和 Voice Profile，并保存为可挂载的 Style Profile。
- **Plot Lab**：把单个 TXT 样本沉淀为全书骨架、分析报告和 Story Engine，并保存为可挂载的 Plot Profile。
- **Project Workbench / Zen Editor**：围绕蓝图、章节、运行时状态、AI 续写、记忆同步与导出组织完整创作流程。

## 典型工作流

1. 在 Provider 配置页接入自己的 OpenAI-compatible 模型网关。
2. 把已有 TXT 样本送入 `Style Lab` 和 `Plot Lab`，生成风格与情节资产。
3. 将生成结果保存成 Profile，并挂载到具体项目。
4. 在项目工作台整理简介、设定、角色、总纲、分卷与章节细纲。
5. 进入 `Zen Editor` 写作、AI 续写、同步记忆，并在需要时导出稿件。

分析任务可在后台安全运行，支持增量日志查看、暂停 / 恢复，离开页面后结果仍会保留在工作台中。

## 界面预览

### 全局 Provider 配置

统一管理多个 OpenAI-compatible Provider，测试连通性、切换默认模型，并始终以掩码形式展示 API Key。

![全局 Provider 配置](./img/FireShot%20Capture%20234%20-%20Persona%20-%20%5Blocalhost%5D.png)

### Style Lab 档案 / Voice Profile

风格分析包含并发处理的分块分析与后处理生成。完成后，可以直接审阅原始分析报告与 Voice Profile，并保存成可复用的 Style Profile。

![Style Lab 分析过程](./img/FireShot%20Capture%20237%20-%20Persona%20-%20%5Blocalhost%5D.png)

![Style Lab 档案 / Voice Profile](./img/FireShot%20Capture%20239%20-%20Persona%20-%20%5Blocalhost%5D.png)

### Plot Lab 档案 / Story Engine

情节分析包含全书骨架构建与核心驱动力提取。Plot Profile 会把原始分析报告、全书骨架与 Story Engine 集中在一起，方便后续项目直接挂载和复用。

![Plot Lab 分析过程](./img/FireShot%20Capture%20238%20-%20Persona%20-%20%5Blocalhost%5D.png)

![Plot Lab 档案 / Story Engine](./img/FireShot%20Capture%20240%20-%20Persona%20-%20%5Blocalhost%5D.png)

### 项目工作台

在进入编辑器前，先在工作台里维护简介、世界观设定、角色卡、总纲、分卷与章节细纲等蓝图信息。

![项目工作台](./img/FireShot%20Capture%20235%20-%20Persona%20-%20%5Blocalhost%5D.png)

### Zen Editor

真正的写作界面：左侧是章节导航，顶部提供导出、同步记忆和 AI 续写入口，用于把约束资产落到正文创作里。

![Zen Editor](./img/FireShot%20Capture%20236%20-%20Persona%20-%20%5Blocalhost%5D.png)

## 技术栈

- 前端：`Next.js 16 App Router` + `React 19` + `TypeScript` + `Tailwind 4` + `TanStack Query`
- 后端：`FastAPI` + `SQLAlchemy` + `Alembic` + `LangChain` + `LangGraph`
- 数据库：本地开发默认使用 `Postgres`（见 `docker-compose.yml`）
- 本地运行：`make dev` 统一拉起数据库、API、Worker 和前端

## 快速开始

本地建议预先安装 `Docker`、`uv` 和 `pnpm`。

### 一键启动（推荐）

```bash
cd Persona
make dev
```

说明：

- 会先检查 Postgres 容器，已运行则跳过启动
- 会检查 `8000/3000` 端口，后端或前端已运行则跳过启动
- 会启动统一后台 Worker，用于消费 `Style Lab` 与 `Plot Lab` 任务
- 首次会自动执行依赖安装（`uv sync`、`pnpm install`）
- 使用 `make status` 查看数据库 / API / Worker / Web 状态
- 使用 `make stop` 停止 API / Worker / Web

打开 `http://localhost:3000`。

<details>
<summary>手动启动数据库、后端、Worker 和前端</summary>

### 1. 启动数据库

```bash
cd Persona
docker compose up -d postgres
```

### 2. 启动后端

```bash
cd Persona/api
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

### 3. 启动 Worker

```bash
cd Persona/api
uv sync
uv run python -m app.worker
```

### 4. 启动前端

```bash
cd Persona/web
cp .env.local.example .env.local
pnpm install
pnpm dev --port 3000
```

</details>

## 验证

```bash
cd Persona/api && uv run pytest -q
cd Persona/web && pnpm test
cd Persona/web && pnpm build
```

## 开发者文档

深入的产品设计、架构、领域实现与开发规范见 [wiki/README.md](./wiki/README.md)。

仓库内的 `wiki/` 是文档事实源，GitHub Wiki 由工作流自动同步。

## 许可证

本仓库采用 [MIT License](./LICENSE)。
