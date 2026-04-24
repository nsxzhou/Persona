# 30 记忆同步（Memory Sync）

## 一句话定义 + 价值

记忆同步是“正文 -> 运行时状态”的闭环。它不是自动改写 Bible，而是先让模型提出一份运行时状态与伏笔追踪的更新草案，再由作者在 Diff Dialog 里决定接受、编辑后接受或忽略。

## 用户视角流程

1. 用户在编辑器里完成一段续写或整章写作。
2. 点击“同步记忆”，或在开启 `auto_sync_memory` 时由系统自动触发。
3. 前端把当前 `runtime_state`、`runtime_threads` 与待检查正文发给后端。
4. 模型返回“完整的新版本运行时状态 + 伏笔追踪”。
5. 如果内容有变化，UI 打开 Diff Dialog；用户确认后才真正写回 `project_bibles.runtime_state` / `runtime_threads`。

## 前端入口与组件链路

主协调点在 `web/components/editor/editor-content-area.tsx`。它从 `useChapterMemorySync()` 里拿到：

- `handleGeneratedContent`
- `handleManualSync`
- `handleAutoChapterSync`
- `openStoredDiff`
- `acceptRuntimeUpdate`

手动触发逻辑也在 `web/components/editor/editor-content-area.tsx`：

- 若当前章已有 `pending_review` 且正文未变，直接打开已有 diff
- 若当前章已是 `synced` / `no_change`，提示可“强制重跑”
- 若正文有未保存修改，先强制保存当前章，再做同步

真正的同步状态机在 `web/hooks/use-chapter-memory-sync.ts:53`：

- `syncContent()` 会调用 `api.proposeBibleUpdate()`，见 `web/hooks/use-chapter-memory-sync.ts:161`
- 手动整章同步在 `web/hooks/use-chapter-memory-sync.ts:216`
- 自动整章同步在 `web/hooks/use-chapter-memory-sync.ts:223`
- 接受提议并写回项目在 `web/hooks/use-chapter-memory-sync.ts:286`

按钮与状态 pill 在 `web/components/memory-sync-button.tsx:129`：

- `pending_review` -> “查看提议”
- `synced` / `no_change` -> 展示“强制重跑”
- `failed` -> 展示“重试同步”

Diff 计算与折叠逻辑由 `web/lib/diff-utils.ts:32` 和 `web/components/bible-diff-dialog.tsx:41` 负责。

## 后端接口 / Service / Repository 链路

后端入口只有一个：`POST /projects/{project_id}/editor/propose-bible-update`，见 `api/app/api/routes/editor.py:78`。

Service 在 `api/app/services/editor.py:230`：

- 先读取项目并确保已配置 Provider
- 再用 `build_bible_update_system_prompt()` 与 `build_bible_update_user_message()` 构造 Prompt
- 最后调用 `invoke_completion()` 返回完整候选文本

Prompt 规则定义在 `api/app/prompts/editor.py` 的 `build_bible_update_system_prompt()` 与 `build_bible_update_user_message()`。解析逻辑在同文件的 `parse_bible_update_response()`：

- 如果模型输出了两个 `##` 区块，就拆成 `runtime_state` 与 `runtime_threads`
- 如果格式退化，所有内容都进 `runtime_state`

章节级同步快照不回写到 `projects`，而是写到 `project_chapters`：

- `ProjectChapterService.update()` 会更新 `memory_sync_status`、`memory_sync_source`、`memory_sync_scope` 等字段，见 `api/app/services/project_chapters.py:112`
- 正文内容 hash 一旦变化，会清掉旧的同步状态，见 `api/app/services/project_chapters.py:105`

## 数据模型

这个领域横跨一张 Bible 表和一张章节表：

- `ProjectBible` 存真实生效的 `runtime_state` 与 `runtime_threads`
- `ProjectChapter` 存“本章最近一次检查结果”的快照

章节表上的状态字段很关键：

- `memory_sync_status`: `pending_review / synced / no_change / failed`
- `memory_sync_source`: `manual / auto`
- `memory_sync_scope`: `generated_fragment / chapter_full`
- `memory_sync_proposed_state` / `memory_sync_proposed_threads`: 待确认版本

这就是为什么用户可以“稍后回来继续看上次提议”，而不用每次都重新跑模型。

## Prompt / LLM 调用要点

记忆同步 Prompt 和普通写作 Prompt 的目标完全不同：

- 它不是续写正文
- 它也不是生成剧情摘要
- 它只提炼“后文必须继续遵守或继续追踪的持续性变化”

`_BIBLE_UPDATE_SYSTEM` 在 `api/app/prompts/editor.py` 里明确要求：

- 只保留持续性变化
- 不记录一次性动作和气氛描写
- 必须输出完整最终版本，不能只写增量
- 严禁“沿用旧内容 / 同上 / 其余不变”这种占位语

这条约束解释了为什么 Memory Sync 看起来像“运行时文档维护助手”，而不是“摘要器”。

## 关键文件索引

- `web/components/zen-editor-view.tsx`
- `web/hooks/use-chapter-memory-sync.ts`
- `web/components/memory-sync-button.tsx`
- `web/components/bible-diff-dialog.tsx`
- `web/lib/diff-utils.ts`
- `api/app/api/routes/editor.py`
- `api/app/services/editor.py`
- `api/app/prompts/editor.py`
- `api/app/services/project_chapters.py`
- `api/app/db/models.py`

## 相关章节

- [22 Zen Editor](./22-zen-editor.md) — 同步按钮和自动触发的位置
- [23 圣经与世界观](./23-bible-worldbuilding.md) — 活态字段属于 Bible 的一部分
- [24 大纲与节拍](./24-outline-and-beats.md) — 逐拍展开结束后也会触发同步
- [31 Prompt ↔ Schema 强绑定](../30-prompt-engineering/31-prompt-schema-coupling.md) — `BibleUpdateRequest/Response` 与 Prompt 契约
