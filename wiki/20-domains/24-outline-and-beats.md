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
- `streamSSE()` 复用了通用 SSE 消费器，见 `web/components/outline-detail-tab.tsx:67`
- `handleGenerateVolumes()` 调 `/editor/generate-volumes` 生成卷级结构，见 `web/components/outline-detail-tab.tsx:95`
- `handleGenerateVolumeChapters()` 调 `/editor/generate-volume-chapters` 生成单卷章节，见 `web/components/outline-detail-tab.tsx:114`

结构化解析依赖 `web/lib/outline-parser.ts:68`：

- 把 Markdown 细纲解析成 `ParsedOutline`
- 前端才能把卷、章、事件、情绪、钩子拆出来用于展示和导航

节拍侧主 UI 在 `web/components/beat-panel.tsx:17`，生成与展开逻辑在 `web/hooks/use-beat-generation.ts:7`：

- `handleGenerateBeats()` 先取当前章光标前文本、运行时状态、细纲和前序章节摘要
- `handleStartBeatExpand()` 再按 beat 顺序逐个请求 `/editor/expand-beat`

## 后端接口 / Service / Repository 链路

大纲和节拍都走 `editor.py`，但分成三类端点：

- 卷结构生成：`api/app/api/routes/editor.py:130`
- 单卷章节生成：`api/app/api/routes/editor.py:143`
- 节拍生成：`api/app/api/routes/editor.py:99`
- 节拍展开：`api/app/api/routes/editor.py:116`

对应的 Service 入口都在 `api/app/services/editor.py:265` 这个 `PlanningEditorService` 里：

- `generate_beats()` 负责非流式返回 beats 列表
- `stream_volume_generation()` 负责卷级结构流式输出
- `stream_volume_chapters_generation()` 负责单卷章节流式输出

真正把 Markdown 细纲解析成结构数据的后端工具是 `api/app/services/outline_parser.py:37`。它和前端 parser 共享同一份格式假设：

- `##` 是卷
- `###` 是章
- `**核心事件** / **情绪走向** / **章末钩子**` 是章节内字段

## 数据模型

大纲数据本体仍然存回 `Project.outline_master` 与 `Project.outline_detail`，对应 `api/app/db/models.py:127`。

章节树同步时会把 `outline_detail` 投影成 `ProjectChapter`，入口见 `api/app/services/project_chapters.py:48`。因此这一领域横跨两层：

- 源文本：`projects.outline_master` / `projects.outline_detail`
- 运行投影：`project_chapters`

## Prompt / LLM 调用要点

这一领域的 Prompt 层分工很清楚：

- `build_volume_generate_system_prompt()` 生成卷级骨架，见 `api/app/services/editor_prompts.py:414`
- `build_volume_chapters_system_prompt()` 生成单卷章节，见 `api/app/services/editor_prompts.py:459`
- `build_beat_generate_system_prompt()` 生成 beats，见 `api/app/services/editor_prompts.py:589`
- `build_beat_expand_system_prompt()` 展开单个 beat，见 `api/app/services/editor_prompts.py:645`

几个重要约束：

- 节拍生成一定会带上 `runtime_state` 和 `runtime_threads`，见 `api/app/services/editor_prompts.py:598`
- 逐拍展开会把“本轮已生成的内容”也作为上下文，避免每一拍像重新开写，见 `api/app/services/editor_prompts.py:657`
- `length_preset` 会影响卷级规划、节拍数量默认值与收束提醒，见 `api/app/services/editor.py:281`

## 关键文件索引

- `web/components/outline-detail-tab.tsx`
- `web/components/beat-panel.tsx`
- `web/hooks/use-beat-generation.ts`
- `web/lib/outline-parser.ts`
- `api/app/api/routes/editor.py`
- `api/app/services/editor.py`
- `api/app/services/editor_prompts.py`
- `api/app/services/outline_parser.py`
- `api/app/services/project_chapters.py`
- `api/app/db/models.py`

## 相关章节

- [21 章节树](./21-chapter-tree.md) — 细纲如何投影为章节记录
- [22 Zen Editor](./22-zen-editor.md) — 节拍面板在编辑器中的位置
- [23 圣经与世界观](./23-bible-worldbuilding.md) — 大纲生成时依赖的蓝图字段
- [28 记忆同步](./28-memory-sync.md) — 节拍展开结束后如何触发活态层同步
- [16 SSE 与流式响应](../10-architecture/16-sse-and-streaming.md) — 卷结构与逐拍展开都走流式通道
