# 22 沉浸编辑器（Zen Editor）

## 一句话定义 + 价值

Zen Editor 是 Persona 的主写作界面。它把章节选择、正文编辑、自动保存、流式续写、节拍驱动写作、记忆同步与导出收拢进一个低干扰工作台里。

## 用户视角流程

1. 用户从项目卡片点击“开始写作”，进入 `/projects/:id/editor`。
2. 编辑器先自动拉取或同步章节树，再选中目标章节。
3. 用户直接写正文，系统在 1 秒防抖后自动保存。
4. 用户可触发 AI 续写，也可先生成节拍再逐拍写作。
5. 续写完成后，如项目开启自动同步记忆，会继续把新增正文送去运行时状态更新。

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
- `web/hooks/use-editor-completion.ts:7` 负责从光标位置发起流式续写
- `web/hooks/use-beat-generation.ts:7` 负责生成节拍与逐拍展开
- `web/hooks/use-chapter-memory-sync.ts:53` 负责续写后或手动触发的记忆同步

辅助组件：

- `web/components/editor-novel-menu.tsx:19` 负责从编辑器快速跳回蓝图/活态字段页
- `web/components/memory-sync-button.tsx` 负责展示同步状态与手动重跑入口
- `web/components/export-project-dialog.tsx:19` 在编辑器右上角提供导出

## 后端接口 / Service / Repository 链路

流式写作路由在 `api/app/api/routes/editor.py`：

- `POST /projects/{project_id}/editor/complete` 用于直接续写
- `POST /projects/{project_id}/editor/generate-section` 用于生成 Bible 区块
- `POST /projects/{project_id}/editor/expand-beat` 用于逐拍展开

正文持久化不走 editor route，而是走章节更新接口：`api/app/api/routes/project_chapters.py:47`。这条路径最终进入 `ProjectChapterService.update()`，见 `api/app/services/project_chapters.py:88`。

真正的写作 Prompt 组装逻辑在 `api/app/services/editor.py:96`：

- `stream_completion()` 会先检查项目已挂载风格档案
- 再读取 `ProjectBible` 中的蓝图字段和活态字段
- 调用 `assemble_writing_context()` 构造完整系统提示词，见 `api/app/services/context_assembly.py:49`
- 最后把消息交给 `LLMProviderService.stream_messages()`

## 数据模型

编辑器横跨三张核心表：

- `Project` 提供默认模型、挂载档案与 `auto_sync_memory`
- `ProjectBible` 提供蓝图字段与活态字段
- `ProjectChapter` 提供当前章正文、字数和记忆同步状态

所以编辑器的状态边界也很清楚：

- “整本书级别”的 Bible 信息写回 `project_bibles`
- “当前章级别”的正文与同步状态写回 `project_chapters`

## Prompt / LLM 调用要点

编辑器是 Prompt 工程最密集的领域之一：

- `api/app/services/context_assembly.py:49` 把 `prompt_pack_payload` 与 Bible 各区块拼成系统提示词
- `WritingEditorService.stream_completion()` 会把 `inspiration / world_building / characters / outline_master / outline_detail / runtime_state / runtime_threads` 全部注入
- `web/hooks/use-editor-completion.ts:46` 只把光标前文本送给模型，不会把光标后文本当成写作上下文

这里的核心哲学是：续写不是“随便让模型接着写”，而是“让模型在完整风格 + 完整约束 + 局部上下文下写”。

## 关键文件索引

- `web/app/(workspace)/projects/[id]/editor/page.tsx`
- `web/components/zen-editor-view.tsx`
- `web/components/editor-novel-menu.tsx`
- `web/hooks/use-editor-autosave.ts`
- `web/hooks/use-editor-completion.ts`
- `web/hooks/use-beat-generation.ts`
- `web/hooks/use-chapter-memory-sync.ts`
- `api/app/api/routes/editor.py`
- `api/app/api/routes/project_chapters.py`
- `api/app/services/editor.py`
- `api/app/services/context_assembly.py`

## 相关章节

- [16 SSE 与流式响应](../10-architecture/16-sse-and-streaming.md) — 流式续写的底层协议
- [21 章节树](./21-chapter-tree.md) — 编辑器如何切章
- [23 圣经与世界观](./23-bible-worldbuilding.md) — 左侧菜单跳回的蓝图与活态字段
- [24 大纲与节拍](./24-outline-and-beats.md) — 逐拍写作的上游
- [30 记忆同步](./30-memory-sync.md) — 自动同步与 Diff 确认
- [31 项目导出](./31-export.md) — 编辑器中的导出按钮
