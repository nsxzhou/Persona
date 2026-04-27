# Persona 项目 Wiki

> 面向开发者的系统化上手文档。产品定位、架构原理、领域实现、Prompt 工程、运维与规范，一网打尽。

Persona 是一个**单用户、BYOK、约束式**的 AI 长篇创作平台。目标不是"一键写小说"，而是把大模型变成一个**受审美约束、有记忆、可驯化**的文字执行器。前后端全部开源在同一仓库内：

- **前端**：Next.js 16 App Router + React 19 + TypeScript + Tailwind 4 + shadcn/ui + TanStack Query + React Hook Form + Zod
- **后端**：FastAPI + SQLAlchemy 2 (async) + Alembic + Pydantic V2 + LangChain + LangGraph
- **存储**：Postgres（开发可用 SQLite）+ 本地文件系统（样本 TXT、原始资产）
- **运行时**：`make dev` 一键拉起 Postgres、后端 API、前端 Next.js，首次会自动 `uv sync` / `pnpm install`

---

## 目录

### 00 概览 — 为什么存在 / 要解决什么

- [00 Persona 是什么](./00-overview/00-what-is-persona.md)
- [01 核心痛点与产品哲学](./00-overview/01-problem-and-philosophy.md)
- [02 系统边界与非目标](./00-overview/02-system-boundary.md)
- [03 MVP 现状与 Roadmap](./00-overview/03-mvp-status-and-roadmap.md)

### 10 架构 — 跨领域的底座与横切

- [10 整体架构总图](./10-architecture/10-high-level-architecture.md)
- [11 后端分层：Router / Service / Repository](./10-architecture/11-backend-layering.md)
- [12 前端架构：App Router / RSC / 数据流](./10-architecture/12-frontend-architecture.md)
- [13 数据模型与迁移](./10-architecture/13-data-model.md)
- [14 鉴权、Session 与资源隔离](./10-architecture/14-auth-and-session.md)
- [15 LLM Provider 接入（BYOK）](./10-architecture/15-llm-provider-integration.md)
- [16 SSE 与流式响应](./10-architecture/16-sse-and-streaming.md)

### 20 业务领域 — 前后端贯通的功能纵切

- [20 项目（Project）](./20-domains/20-projects.md)
- [21 章节树（Chapter Tree）](./20-domains/21-chapter-tree.md)
- [22 沉浸编辑器（Zen Editor）](./20-domains/22-zen-editor.md)
- [23 圣经（Bible）与世界观](./20-domains/23-bible-worldbuilding.md)
- [24 大纲与节拍（Outline & Beats）](./20-domains/24-outline-and-beats.md)
- [25 概念抽卡（Concept Gacha）](./20-domains/25-concept-gacha.md)
- [26 Style Lab：文风实验室](./20-domains/26-style-lab.md)
- [27 Style Analysis 管道（LangGraph）](./20-domains/27-style-analysis-pipeline.md)
- [28 Plot Lab：情节实验室](./20-domains/28-plot-lab.md)
- [29 Plot Analysis 管道（LangGraph）](./20-domains/29-plot-analysis-pipeline.md)
- [30 记忆同步（Memory Sync）](./20-domains/30-memory-sync.md)
- [31 项目导出（txt / epub）](./20-domains/31-export.md)

### 30 Prompt 工程

- [30 Prompt 语料总览](./30-prompt-engineering/30-prompt-overview.md)
- [31 Prompt ↔ Schema 强绑定规约](./30-prompt-engineering/31-prompt-schema-coupling.md)
- [32 ANALYZE-GENERATE 手法论](./30-prompt-engineering/32-analyze-generate-playbook.md)

### 40 运维与部署

- [40 本地开发与 Makefile](./40-operations/40-local-dev-and-make.md)
- [41 数据库与 Alembic 迁移](./40-operations/41-database-and-migrations.md)
- [42 配置与环境变量](./40-operations/42-configuration.md)

### 50 规范与流程

- [50 编码规范（叙事向导）](./50-standards/50-coding-standards.md) — 权威规则见根目录 `AGENT.md`
- [51 测试策略](./50-standards/51-testing-strategy.md)
- [52 贡献与 Git 流程](./50-standards/52-contribution-workflow.md)

### 90 附录

- [90 术语表](./90-glossary/90-glossary.md)
- [91 常见问题与调试 FAQ](./90-glossary/91-faq.md)

---

## 按角色阅读路径

### 🆕 新贡献者（从零建立心智模型，1–2 天）

完整顺序走一遍，建立"产品 → 架构 → 领域 → 规范"的四层心智：

1. `00-overview/` 全部四篇 — 明白 Persona 要解决什么问题、系统边界、当前进度
2. `10-architecture/10-high-level-architecture.md` → `11-backend-layering.md` → `12-frontend-architecture.md` — 三张关键图先看
3. `10-architecture/13-data-model.md` — 所有领域都靠这些表
4. `20-domains/20-projects.md` → `21-chapter-tree.md` → `22-zen-editor.md` — 最简纵切链路
5. `20-domains/26-style-lab.md` → `27-style-analysis-pipeline.md` — 项目里最复杂的子系统，吃透它就吃透了本项目的 LangGraph 用法；想进一步看带骨架预览的变体，接着看 `28-plot-lab.md` → `29-plot-analysis-pipeline.md`
6. `30-prompt-engineering/` 三篇 + `50-standards/50-coding-standards.md` — 约束规则与落地范式
7. `40-operations/` 全部 — 确保你能本地跑起来并调试

### 🔧 仅做后端（API / Service / LangGraph）

- `10-architecture/11-backend-layering.md`
- `10-architecture/13-data-model.md`
- `10-architecture/14-auth-and-session.md`
- `10-architecture/15-llm-provider-integration.md`
- `20-domains/27-style-analysis-pipeline.md`（LangGraph 最深的案例）
- `30-prompt-engineering/31-prompt-schema-coupling.md`
- `50-standards/50-coding-standards.md`（后端部分）+ 根目录 `AGENT.md`

### 🎨 仅做前端（Next.js / React / Hooks）

- `10-architecture/12-frontend-architecture.md`
- `10-architecture/16-sse-and-streaming.md`
- `20-domains/22-zen-editor.md`
- `20-domains/23-bible-worldbuilding.md`
- `20-domains/24-outline-and-beats.md`
- `20-domains/26-style-lab.md`（Wizard + 实时日志的交互案例）
- `50-standards/50-coding-standards.md`（前端部分）+ 根目录 `AGENT.md`

### 🧪 只想上手跑测试

- `40-operations/40-local-dev-and-make.md`
- `40-operations/41-database-and-migrations.md`
- `50-standards/51-testing-strategy.md`

---

## 文档约定

### 代码引用

优先使用“`文件路径 + 关键符号 / 路由 / 组件名`”的稳定引用方式，例如：

- `api/app/api/routes/novel_workflows.py` 中的 `create_novel_workflow()`
- `web/components/workbench-tabs.tsx` 中的 `OutlineDetailTab`

只有在字段、迁移号或小型工具函数这类相对稳定的位置，才补充 `路径:行号`。发现 wiki 与代码不一致时，应以代码为准并修复本文档。

### 图表

架构图、数据流、状态机、LangGraph 管道全部使用 **Mermaid**（GitHub / VS Code / 主流 Markdown 预览器都原生支持）。

### 语言与术语

正文中文为主，技术术语保留英文（FastAPI、LangGraph、Zen Editor、Voice Profile 等）。业务术语（圣经、大纲、节拍、风格档案等）的严格定义请查 [90 术语表](./90-glossary/90-glossary.md)。

### 模板

- **领域章节（20-domains/）**：纵切七段——定义、用户流程、前端链路、后端链路、数据模型、Prompt/LLM、相关文件索引
- **横切章节（10/30/40/50）**：概念四段——要解决的问题、关键概念与约束、实现位置与扩展点、常见坑

---

## 与根目录其它文档的关系

| 文件 | 用途 | 与本 wiki 关系 |
| --- | --- | --- |
| `README.md` | 项目门面、快速启动 | 顶部链到此 wiki；启动命令等内容保留在根 README |
| `AGENT.md` | AI 工具 / 人类贡献者的**最高级编码约束** | wiki 中 `50-coding-standards.md` 是叙事向导，**权威规则以根目录 AGENT.md 为准** |
| `ANALYZE-GENERATE.md` | 原始 Prompt 工程方法论 | 内容已吸纳进 `30-prompt-engineering/32-analyze-generate-playbook.md`，原根级文件已删除 |
| `Persona-约束式文风模仿长篇创作系统设计.md` | 产品设计文档 | 内容已拆进 `00-overview/` 与各领域章节，原根级文件已删除 |

---

## 贡献 wiki 本身

- 修改后在 GitHub 或 VS Code Markdown Preview 里确认 Mermaid 图渲染正常
- 更新代码引用时，优先确认文件、符号名与路由名是否仍然存在；只有确实保留行号时才刷新行号
- 新增文章时，**必须**在本 `README.md` 的目录 + 对应角色阅读路径里同步新增链接
- 文章标题用"章节号 + 中文标题"双语并置（目录链接显示中文，文件名用英文拼写）
