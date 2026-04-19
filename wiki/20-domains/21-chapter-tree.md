# 21 章节树（Chapter Tree）

## 一句话定义 + 价值

章节树是 `outline_detail` 的结构化投影层。它把 Markdown 大纲同步成可选中、可保存正文、可带记忆同步状态的 `project_chapters` 记录，支撑 Zen Editor 的导航与写作粒度。

## 用户视角流程

1. 用户先在项目工作台里生成或手写 `outline_detail`。
2. 打开编辑器时，前端先拉取现有章节；如果为空，就自动调用“按大纲同步章节”。
3. 左侧章节树展示卷、章、完成进度与当前选中态。
4. 选择章节后，正文区切到该章节内容；保存时按章节粒度更新 `project_chapters`。

## 前端入口与组件链路

树形 UI 在 `web/components/chapter-tree.tsx:15`：

- 卷支持折叠/展开
- 当前卷统计完成章节数，见 `web/components/chapter-tree.tsx:48`
- 当前选中章会额外展示核心事件、情绪走向和章末钩子，见 `web/components/chapter-tree.tsx:125`

编辑器在 `web/components/zen-editor-view.tsx:314` 首次加载时会：

- 先 `api.getProjectChapters(project.id)`
- 若列表为空，再 fallback 到 `api.syncProjectChapters(project.id)`

这保证“有大纲但没同步章节”不会把用户卡死在空白导航里。

## 后端接口 / Service / Repository 链路

路由都在 `api/app/api/routes/project_chapters.py`：

- 列表：`api/app/api/routes/project_chapters.py:18`
- 从大纲同步：`api/app/api/routes/project_chapters.py:31`
- 单章更新：`api/app/api/routes/project_chapters.py:47`

Service 在 `api/app/services/project_chapters.py`：

- `list()` 先校验项目存在，再按项目返回章节，见 `api/app/services/project_chapters.py:38`
- `sync_outline()` 读取 `project.outline_detail`，用 `parse_outline()` 解析出卷/章结构，再按 `(volume_index, chapter_index)` 做 upsert，见 `api/app/services/project_chapters.py:48`
- `update()` 既负责正文落库，也负责在内容 hash 变化时清空旧的记忆同步状态，见 `api/app/services/project_chapters.py:88`

这里最重要的约束是：章节树的“主排序键”不是标题，而是 `(volume_index, chapter_index)`。

## 数据模型

对应的 ORM 模型是 `api/app/db/models.py:174` 的 `ProjectChapter`。它存的不只是标题和正文，还存三类状态：

- 结构信息：`volume_index`、`chapter_index`、`title`
- 写作状态：`content`、`word_count`
- 记忆同步状态：`memory_sync_status`、`memory_sync_source`、`memory_sync_scope`、`memory_sync_*`

这让章节树不只是导航组件，而是“写作单元 + 状态快照”的持久层。

## Prompt / LLM 调用要点

章节树本身不直接调用 LLM，但它是后续两类 AI 流程的上下文源：

- 节拍生成与逐拍展开会读取当前章节与前序章节上下文，入口在 `web/hooks/use-beat-generation.ts:45`
- 编辑器续写会把当前章节光标前文本、当前章节结构和前序章节尾部拼成用户消息，入口在 `web/hooks/use-editor-completion.ts:53`

也就是说，`project_chapters` 决定了“LLM 看到的是哪一章、前文能看到多少、该把结果写回哪一章”。

## 关键文件索引

- `web/components/chapter-tree.tsx`
- `web/components/zen-editor-view.tsx`
- `api/app/api/routes/project_chapters.py`
- `api/app/services/project_chapters.py`
- `api/app/services/outline_parser.py`
- `api/app/db/models.py`

## 相关章节

- [20 项目](./20-projects.md) — 章节树依附于项目
- [22 Zen Editor](./22-zen-editor.md) — 章节树如何驱动正文编辑
- [24 大纲与节拍](./24-outline-and-beats.md) — `outline_detail` 如何变成章节结构
- [28 记忆同步](./28-memory-sync.md) — 章节级别的 `memory_sync_*` 字段含义
