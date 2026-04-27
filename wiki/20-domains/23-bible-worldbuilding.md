# 23 圣经（Bible）与世界观

## 一句话定义 + 价值

Bible 是 Persona 的“蓝图层 + 活态层”创作资产面板。它既承载作者手工维护的长期设定，也承载 AI 根据正文提议更新的运行时记忆。

## 用户视角流程

1. 用户在项目详情页的不同 tab 中编辑灵感、世界观、角色、总纲、细纲。
2. 当某个字段为空时，可以插入模板或直接让 AI 生成。
3. 运行时字段不是靠手工长时间维护，而是由正文写作后触发 AI 提议更新，再通过 Diff Dialog 人工确认。
4. 这些字段会持续回流到后续续写、节拍与大纲 Prompt 中。

## 前端入口与组件链路

Bible 的字段元数据集中在 `web/lib/bible-fields.ts:35`：

- 蓝图字段：`inspiration`、`world_building`、`characters`、`outline_master`、`outline_detail`
- 活态字段：`runtime_state`、`runtime_threads`

单个字段的编辑器由 `web/components/bible-tab-content.tsx:38` 负责：

- 空状态下提供“AI 生成”与“使用模板”
- 非空状态下支持编辑 / 预览切换
- 模板内容来自 `web/lib/bible-templates.ts:3`

运行时 diff 确认弹窗在 `web/components/bible-diff-dialog.tsx:41`：

- 左右双栏展示当前内容和提议内容
- 支持“只看改动”
- 支持在接受前直接编辑 AI 提议文本

## 后端接口 / Service / Repository 链路

Bible 字段有专门的读取/更新入口，位于 `api/app/api/routes/projects.py`：

- `GET /api/v1/projects/{id}/bible`
- `PATCH /api/v1/projects/{id}/bible`

项目元数据（名称、默认 Provider、挂载档案等）仍然走 `PATCH /api/v1/projects/{id}`；Bible 长文本本体不再混在 `projects` 表里。

AI 生成蓝图字段与活态初稿走 novel workflow：

- `POST /api/v1/novel-workflows`，`intent_type=section_generate`

生成逻辑在 `api/app/services/novel_workflow_pipeline.py`：

- worker 先取挂载的 `voice_profile_payload` 与 `story_engine_payload`
- `ContextSelectorAgent` 选择项目描述、蓝图字段与活态字段
- `build_section_system_prompt()` 按字段名选择不同的 Prompt 模板，实现位于 `api/app/prompts/section_router.py`
- `build_section_user_message()` 把其它 Bible 区块作为上下文注入，实现位于 `api/app/prompts/section_router.py`

## 数据模型

Bible 已拆成独立的 `ProjectBible` 表，与 `Project` 形成 1:1 关系。这条边界的含义是：

- 蓝图字段是“整本书级别”的长期资产，天然属于项目
- 活态字段也是“整本书当前运行时状态”，不是单章私有数据

这样带来的好处是：

- 项目元数据（Provider、挂载档案、长度偏好）与长文本 Bible 内容分层更清晰
- `PATCH /api/v1/projects/{id}` 和 `PATCH /api/v1/projects/{id}/bible` 的职责边界更明确
- 作者仍然可以在同一个工作台 UI 下维护所有长期约束和运行时记忆

## Prompt / LLM 调用要点

Bible 是 Prompt 组装的主燃料：

- `api/app/services/context_assembly.py:49` 会按 `BIBLE_SECTION_ORDER` 把非空字段依次拼进系统提示词
- `api/app/prompts/section_router.py` 根据 section 路由到 `world_building.py`、`characters.py`、`outline.py`、`chapter_plan.py` 等专职 prompt
- `world_building` 和 `characters_blueprint` 的方法论分别落在 `api/app/prompts/world_building.py` 与 `api/app/prompts/characters.py`

其中最重要的边界是：

- 蓝图层是作者手编的长期规划，AI 生成只是起草工具
- 活态层是对已发生正文的“短期运行时记忆”，不是Story Engine，也不是大纲副本

## 关键文件索引

- `web/lib/bible-fields.ts`
- `web/lib/bible-templates.ts`
- `web/components/bible-tab-content.tsx`
- `web/components/bible-diff-dialog.tsx`
- `api/app/api/routes/projects.py`
- `api/app/api/routes/novel_workflows.py`
- `api/app/services/novel_workflow_pipeline.py`
- `api/app/services/novel_workflow_agents.py`
- `api/app/prompts/section_router.py`
- `api/app/services/context_assembly.py`
- `api/app/db/models.py`

## 相关章节

- [20 项目](./20-projects.md) — Project 与 `ProjectBible` 的 1:1 业务关系
- [22 Zen Editor](./22-zen-editor.md) — 编辑器如何消费这些字段
- [24 大纲与节拍](./24-outline-and-beats.md) — `outline_master` / `outline_detail` 的专门链路
- [30 记忆同步](./30-memory-sync.md) — 活态字段如何由正文回写
- [31 Prompt ↔ Schema 强绑定](../30-prompt-engineering/31-prompt-schema-coupling.md) — Prompt 模板与结构化契约
