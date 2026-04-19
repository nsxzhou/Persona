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

蓝图字段本身没有专门 Router，它们直接作为 `Project` 的文本列，经 `PATCH /api/v1/projects/{id}` 更新，入口见 `api/app/api/routes/projects.py:78`。

AI 生成蓝图字段与活态初稿走 editor route：

- `POST /projects/{project_id}/editor/generate-section`，见 `api/app/api/routes/editor.py:64`

生成逻辑在 `api/app/services/editor.py:150`：

- `_get_style_prompt()` 先取挂载的风格约束
- `build_section_system_prompt()` 按字段名选择不同的 Prompt 模板，见 `api/app/services/editor_prompts.py:316`
- `build_section_user_message()` 把其它 Bible 区块作为上下文注入，见 `api/app/services/editor_prompts.py:363`

## 数据模型

Bible 没有独立表，全部直接挂在 `api/app/db/models.py:127` 的 `Project` 上。这是一个很有意图的设计：

- 蓝图字段是“整本书级别”的长期资产，天然属于项目
- 活态字段也是“整本书当前运行时状态”，不是单章私有数据

这样带来的好处是：

- 不需要额外 join 就能组装完整写作上下文
- 作者可以把所有长期约束和运行时记忆放在同一个项目壳里维护

## Prompt / LLM 调用要点

Bible 是 Prompt 组装的主燃料：

- `api/app/services/context_assembly.py:49` 会按 `BIBLE_SECTION_ORDER` 把非空字段依次拼进系统提示词
- `api/app/services/editor_prompts.py:180` 开始的 `_SECTION_META` 为每个字段定义不同的生成任务
- `world_building` 和 `characters` 还会附带“题材收束提醒”，避免模型凭空补完一套超自然体系，见 `api/app/services/editor_prompts.py:171`

其中最重要的边界是：

- 蓝图层是作者手编的长期规划，AI 生成只是起草工具
- 活态层是对已发生正文的“短期运行时记忆”，不是剧情摘要，也不是大纲副本

## 关键文件索引

- `web/lib/bible-fields.ts`
- `web/lib/bible-templates.ts`
- `web/components/bible-tab-content.tsx`
- `web/components/bible-diff-dialog.tsx`
- `api/app/api/routes/projects.py`
- `api/app/api/routes/editor.py`
- `api/app/services/editor.py`
- `api/app/services/editor_prompts.py`
- `api/app/services/context_assembly.py`
- `api/app/db/models.py`

## 相关章节

- [20 项目](./20-projects.md) — Bible 字段都挂在 `projects` 上
- [22 Zen Editor](./22-zen-editor.md) — 编辑器如何消费这些字段
- [24 大纲与节拍](./24-outline-and-beats.md) — `outline_master` / `outline_detail` 的专门链路
- [28 记忆同步](./28-memory-sync.md) — 活态字段如何由正文回写
- [31 Prompt ↔ Schema 强绑定](../30-prompt-engineering/31-prompt-schema-coupling.md) — Prompt 模板与结构化契约
