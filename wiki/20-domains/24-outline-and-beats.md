# 24 大纲与节拍（Outline & Beats）

## 一句话定义 + 价值

这一领域负责把“总纲 -> 分卷结构 -> 章节细纲 -> 本章节拍 -> 逐拍正文”串成一条渐进式写作流水线，让作者先规划，再让模型执行。

## 用户视角流程

1. 用户先填或生成 `outline_master`。
2. 在 `outline_detail` 页里生成分卷结构，再为某一卷生成章节细纲。
3. 编辑器读取结构化细纲后，用户可以针对当前章生成 5-10 条节拍。
4. 用户确认节拍后，系统按顺序逐拍展开成正文。

## 前端入口与组件链路

`outline_detail` 的主 UI 在 `web/components/outline-detail-tab.tsx:37`：

- 支持“编辑 / 预览 / 结构化视图”三种模式
- 分卷与章节细纲生成通过 `api.runVolumeWorkflow()` / `api.runVolumeChaptersWorkflow()` 创建 workflow run
- 页面可通过 `NovelWorkflowRunPanel` 查看 run 状态、日志、产物与 warning

结构化解析依赖 `web/lib/outline-parser.ts:68`：

- 把 Markdown 细纲解析成 `ParsedOutline`
- 前端才能把卷、章、事件、情绪、钩子拆出来用于展示和导航

节拍侧主 UI 在 `web/components/beat-panel.tsx:17`，生成与展开逻辑在 `web/hooks/use-beat-generation.ts:7`：

- `handleGenerateBeats()` 先取当前章光标前文本、运行时状态、细纲和前序章节摘要
- `handleStartBeatExpand()` 再按 beat 顺序创建 `beat_expand` workflow run

## 后端接口 / Service / Repository 链路

大纲和节拍都走 novel workflow，但分成不同 intent：

- 卷结构生成：`intent_type=volume_generate`
- 单卷章节生成：`intent_type=volume_chapters_generate`
- 节拍生成：`intent_type=beats_generate`
- 节拍展开：`intent_type=beat_expand`

对应的编排在 `api/app/services/novel_workflow_pipeline.py` 与 `api/app/services/novel_workflow_agents.py`：

- `BeatAgent.generate()` 负责生成 beats Markdown
- `BeatAgent.expand()` 负责逐拍正文
- 卷结构和章节细纲由 pipeline 调用 `outline.py` / `chapter_plan.py` prompt builders

真正把 Markdown 细纲解析成结构数据的后端工具是 `api/app/services/outline_parser.py:37`。它和前端 parser 共享同一份格式假设：

- `##` 是卷
- `###` 是章
- `**核心事件** / **情绪走向** / **章末钩子**` 是章节内字段

## 数据模型

大纲数据本体仍然存回 `ProjectBible.outline_master` 与 `ProjectBible.outline_detail`。

章节树同步时会把 `outline_detail` 投影成 `ProjectChapter`，入口见 `api/app/services/project_chapters.py:48`。因此这一领域横跨两层：

- 源文本：`project_bibles.outline_master` / `project_bibles.outline_detail`
- 运行投影：`project_chapters`

## Prompt / LLM 调用要点

这一领域的 Prompt 层分工很清楚：

- `build_volume_generate_system_prompt()` 生成卷级骨架，实现位于 `api/app/prompts/outline.py`
- `build_volume_chapters_system_prompt()` 生成单卷章节，实现位于 `api/app/prompts/chapter_plan.py`
- `build_beat_generate_system_prompt()` 生成 beats，实现位于 `api/app/prompts/beat.py`
- `build_beat_expand_system_prompt()` 展开单个 beat，实现位于 `api/app/prompts/prose_writer.py`

几个重要约束：

- 节拍生成的 user message 会显式带上 `runtime_state`、`runtime_threads`、当前章上下文与前序章节上下文
- 逐拍展开会把 `preceding_beats_prose` 和“本轮已生成的内容”也作为上下文，避免每一拍像重新开写
- `length_preset` 在规划层只作为弱提示，不再切换世界观/角色/总纲/细纲的硬分支模板；运行期仍会影响节拍数量默认值、展开字数与收束提醒

## 关键文件索引

- `web/components/outline-detail-tab.tsx`
- `web/components/beat-panel.tsx`
- `web/hooks/use-beat-generation.ts`
- `web/lib/outline-parser.ts`
- `web/components/novel-workflow-run-panel.tsx`
- `api/app/api/routes/novel_workflows.py`
- `api/app/services/novel_workflow_pipeline.py`
- `api/app/services/novel_workflow_agents.py`
- `api/app/prompts/outline.py`
- `api/app/prompts/chapter_plan.py`
- `api/app/prompts/beat.py`
- `api/app/prompts/prose_writer.py`
- `api/app/services/outline_parser.py`
- `api/app/services/project_chapters.py`
- `api/app/db/models.py`

## 相关章节

- [21 章节树](./21-chapter-tree.md) — 细纲如何投影为章节记录
- [22 Zen Editor](./22-zen-editor.md) — 节拍面板在编辑器中的位置
- [23 圣经与世界观](./23-bible-worldbuilding.md) — 大纲生成时依赖的蓝图字段
- [30 记忆同步](./30-memory-sync.md) — 节拍展开结束后如何触发活态层同步
- [16 SSE 与流式响应](../10-architecture/16-sse-and-streaming.md) — 卷结构与逐拍展开都走流式通道
