# 50 编码规范（叙事向导）

> 权威规则以根目录 `AGENT.md` 为准。本章只是面向开发者的叙事性索引，不替代原文。

## 要解决什么问题

Persona 的代码量不算巨大，但约束很硬。如果不了解这些约束，最容易出现三种问题：

- Router / Service / Repository 职责串台
- Prompt 改了但 Schema 或前端类型没同步
- 前端把本该 Server 的逻辑抬到 Client，导致边界失控

## 关键概念与约束

### 后端：严格三层，不要偷懒

`AGENT.md:19` 明确要求：

- Router 只收参数、做依赖注入、返回响应
- Service 放业务逻辑
- Repository 只管数据库交互

在代码里最典型的参考实现是：

- `api/app/api/routes/projects.py:29`
- `api/app/services/projects.py:15`
- `api/app/db/repositories/projects.py:26`

如果你在 Router 里写了长段查询，或者在 Repository 里做跨表业务决策，基本就是偏离项目约束。

### 后端：坚持现代类型、Pydantic V2 和 `Annotated`

`AGENT.md:25` 到 `28` 定了三条硬规则：

- 用 Python 3.11+ 类型写法
- FastAPI 依赖注入用 `Annotated`
- Pydantic 走 V2 API，不用 V1 老方法

代表性样例在 `api/app/api/deps.py:21` 和 `api/app/schemas/editor.py:12`。

### 后端：数据库默认异步、默认防 N+1

`AGENT.md:30` 到 `37` 要求：

- 只用 SQLAlchemy 2.0 异步风格
- 常规请求由 `get_db_session()` 统一 commit/rollback
- 复杂事务和后台任务使用显式上下文
- 处理关联数据时优先 `selectinload` / `joinedload`

参考点：

- `api/app/db/session.py:23`
- `api/app/services/style_analysis_worker.py:85`
- `api/app/db/repositories/projects.py:37`

### Prompt / Schema / 状态机是高风险区

`AGENT.md:39` 到 `45` 专门为 LLM 管道立规矩：

- Prompt 与 Schema 强绑定
- 不要在循环或节点里重复实例化 LLM 客户端
- LangGraph state 必须是纯数据，不挂 Session 和连接对象

对应代码样例：

- `api/app/services/style_analysis_llm.py:87`
- `api/app/services/style_analysis_pipeline.py:46`
- `api/app/schemas/style_analysis_jobs.py:27`

### 前端：默认 Server Component，状态下放到叶子

`AGENT.md:61` 到 `65` 是前端最常用的边界规则：

- 默认 Server Components
- 只在真需要状态或浏览器 API 时才写 `'use client'`
- Client 状态尽量下放到叶子

参考实现：

- `web/app/(workspace)/layout.tsx:8`
- `web/components/app-shell.tsx:16`
- `web/components/zen-editor-view.tsx:1`

### 前端：表单与样式也有固定套路

`AGENT.md:67` 到 `78` 要求：

- 表单优先 `react-hook-form + zod`
- 动态类名用 `cn`
- 多变体组件用 `cva`

代表性样例：

- `web/components/provider-config-form-dialog.tsx:31`
- `web/components/project-form.tsx:57`
- `web/lib/validations/provider.ts:12`
- `web/lib/validations/style-lab.ts:3`

## 实现位置与扩展点

### 开发时的最短自检清单

提交前至少问自己五个问题：

1. 我有没有把业务逻辑塞进 Router？
2. 我改 Prompt 时，Schema / parser / 前端类型有没有一起改？
3. 我有没有让 Repository 偷做业务决策？
4. 我有没有把不该上浏览器的逻辑写进 `'use client'` 文件？
5. 我有没有先读现有实现再改？

### 何时优先查 `AGENT.md`

以下场景不要靠记忆，直接回看原文：

- 改数据库事务或异步模式
- 改 Prompt 与大模型输出契约
- 改前端 RSC / Server Action / React Query 边界
- 改测试与交付方式

## 常见坑 / 调试指南

| 坑 | 为什么危险 | 参考修法 |
| --- | --- | --- |
| 手写一套和 OpenAPI 同构的 TS 类型 | 迟早漂移 | 走 `web/lib/api/generated/openapi.ts` |
| 在 LangGraph state 里塞 DB session | 无法序列化、断点恢复失效 | 只存纯数据字段 |
| 在项目列表查询里把大 Text 全部带出来 | 列表页性能变差 | 参考 `list_summaries()` |
| 前端组件顶层一把 `'use client'` | JS 体积膨胀、边界变脏 | 把状态往叶子压 |

## 相关章节

- [11 后端分层](../10-architecture/11-backend-layering.md)
- [12 前端架构](../10-architecture/12-frontend-architecture.md)
- [31 Prompt ↔ Schema 强绑定](../30-prompt-engineering/31-prompt-schema-coupling.md)
- [51 测试策略](./51-testing-strategy.md)
- 根目录 `AGENT.md`
