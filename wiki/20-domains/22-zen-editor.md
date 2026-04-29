# 22 沉浸编辑器（Zen Editor）

## 一句话定义 + 价值

Zen Editor 是 Persona 的主写作界面。它把章节选择、正文编辑、自动保存、选区局部改写、节拍驱动写作、记忆同步与导出收拢进一个低干扰工作台里。

## 用户视角流程

1. 用户从项目卡片点击“开始写作”，进入 `/projects/:id/editor`。
2. 编辑器先自动拉取或同步章节树，再选中目标章节。
3. 用户直接写正文，系统在 1 秒防抖后自动保存。
4. 用户先生成节拍并逐拍展开完整章节。
5. 用户选中正文片段后触发局部改写，输入修改要求，预览确认后替换选区。

## 前端入口与组件链路

页面入口是 `web/app/(workspace)/projects/[id]/editor/page.tsx`。它先在服务端拿到：

- 项目本体
- 当前挂载风格档案名（如果有）
- 初始章节定位和意图参数

页面先把项目、Project Bible、可选的 active profile 名称以及初始章节定位交给 `web/components/zen-editor-view.tsx`。`ZenEditorView` 进一步把这些状态交给 `EditorProvider` 与 `EditorContentArea`，真正的编辑器 UI 已拆到 `web/components/editor/` 子目录下，而不是继续堆在单一大组件里。

当前编辑器内部同时持有：

- `chapters` 与 `currentChapter`
- 当前 textarea 内容与已保存内容
- 左侧章节导航和右侧节拍面板开合状态
- 记忆同步 diff dialog 状态

几个关键 hook 分工如下：

- `web/hooks/use-editor-autosave.ts:8` 负责 1 秒防抖自动保存、切章前 flush、手动 `saveNow()`
- `web/hooks/use-selection-rewrite.ts:7` 负责选区局部改写
- `web/hooks/use-beat-generation.ts:7` 负责生成节拍与逐拍展开
- `web/hooks/use-chapter-memory-sync.ts:53` 负责节拍写作后或手动触发的记忆同步

辅助组件：

- `web/components/editor-novel-menu.tsx:19` 负责从编辑器快速跳回蓝图/活态字段页
- `web/components/memory-sync-button.tsx` 负责展示同步状态与手动重跑入口
- `web/components/export-project-dialog.tsx:19` 在编辑器右上角提供导出

## 后端接口 / Service / Repository 链路

编辑器 AI 能力统一走 `api/app/api/routes/novel_workflows.py`：

- `POST /api/v1/novel-workflows` 创建 `selection_rewrite`、`beats_generate`、`beat_expand`、`memory_refresh` 等 run
- `GET /api/v1/novel-workflows/{id}/status` 轮询 run 状态、阶段、断点与产物列表
- `GET /api/v1/novel-workflows/{id}/logs` 读取任务日志
- `GET /api/v1/novel-workflows/{id}/artifacts/{artifact_name}` 读取正文、节拍、记忆更新等 Markdown 产物
- `POST /api/v1/novel-workflows/{id}/pause|resume|decision` 处理暂停、恢复和人工确认

正文持久化仍走章节更新接口：`api/app/api/routes/project_chapters.py`。AI run 产物由前端确认后写回章节或 Bible。

真正的写作流程在 `api/app/services/novel_workflow_pipeline.py` 与 `api/app/services/novel_workflow_agents.py`：

- `NovelWorkflowPipeline` 负责编排 LangGraph 节点、断点、artifact 与持久化 payload
- `ContextSelectorAgent` 提取项目、Bible 与章节上下文
- `BeatAgent`、`EditorAgent`、`MemorySyncAgent` 等专职 agent 调用各自 prompt 模块
- `assemble_writing_context()` 仍负责正文生成时的系统上下文拼装，见 `api/app/services/context_assembly.py`

## 数据模型

编辑器横跨三张核心表：

- `Project` 提供默认模型、挂载档案与 `auto_sync_memory`
- `ProjectBible` 提供蓝图字段与活态字段
- `ProjectChapter` 提供当前章正文、字数和记忆同步状态

所以编辑器的状态边界也很清楚：

- “整本书级别”的 Bible 信息写回 `project_bibles`
- “当前章级别”的正文与同步状态写回 `project_chapters`

## 上下文注入 (Context Injection)

编辑器是 Prompt 工程最密集的领域之一，真正的上下文组装高度依赖于 `GenerationProfile`（生成配置）：

- **动态目标与欲望计算**：在 workflow pipeline 生成正文时，系统会根据 `GenerationProfile` 动态计算出本章的写作目标卡片（`ChapterObjectiveCard`）以及包含欲望叠加规则的表达强度（`IntensityProfile`），从而决定当前剧情的推进方向与张力类型。
- **系统提示词组装**：`api/app/services/context_assembly.py` 负责将上述计算出的动态目标与欲望，连同挂载的风格档案（`voice_profile_payload`）、剧情引擎（`story_engine_payload`）以及 Bible 的各个区块（如 `world_building`、`outline_detail`、`runtime_state` 等）拼装成完整的系统提示词。
- **局部正文上下文**：前端 `web/hooks/use-selection-rewrite.ts` 发起局部改写时，会把选中文本、选区前文、选区后文、章节上下文和用户修改要求一起送给模型。

这里的核心哲学是：章节正文由节拍链路生成完整草稿，后续 AI 只针对作者选中的片段做可确认、可回滚的局部改写。

## 关键文件索引

- `web/app/(workspace)/projects/[id]/editor/page.tsx`
- `web/components/zen-editor-view.tsx`
- `web/components/editor-novel-menu.tsx`
- `web/hooks/use-editor-autosave.ts`
- `web/hooks/use-selection-rewrite.ts`
- `web/hooks/use-beat-generation.ts`
- `web/hooks/use-chapter-memory-sync.ts`
- `web/components/editor/selection-rewrite-dialog.tsx`
- `web/components/novel-workflow-run-panel.tsx`
- `api/app/api/routes/novel_workflows.py`
- `api/app/api/routes/project_chapters.py`
- `api/app/services/novel_workflow_pipeline.py`
- `api/app/services/novel_workflow_agents.py`
- `api/app/services/context_assembly.py`

## 相关章节

- [21 章节树](./21-chapter-tree.md) — 编辑器如何切章
- [23 圣经与世界观](./23-bible-worldbuilding.md) — 左侧菜单跳回的蓝图与活态字段
- [24 大纲与节拍](./24-outline-and-beats.md) — 逐拍写作的上游
- [30 记忆同步](./30-memory-sync.md) — 自动同步与 Diff 确认
- [31 项目导出](./31-export.md) — 编辑器中的导出按钮
