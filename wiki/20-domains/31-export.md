# 31 项目导出（txt / epub）

## 一句话定义 + 价值

导出功能把当前项目的章节正文打包成可交付文本，让用户能把 Persona 里的创作结果带出系统，而不被锁死在编辑器 UI 中。

## 用户视角流程

1. 用户在项目列表卡片或编辑器里点击“导出”。
2. 弹窗里选择 TXT 或 EPUB。
3. 浏览器请求 `/api/v1/projects/{id}/export?format=...`。
4. 后端按当前章节顺序拼接内容并返回流式下载响应。

## 前端入口与组件链路

通用弹窗组件在 `web/components/export-project-dialog.tsx:19`：

- `handleExport()` 调 `api.exportProject(projectId, format)`，见 `web/components/export-project-dialog.tsx:31`
- 浏览器侧把 Blob 转成临时下载链接并触发下载
- 导出成功后关闭弹窗并 toast 提示

它在两个地方被复用：

- 项目列表卡片，见 `web/components/projects-page-view.tsx:228`
- Zen Editor 顶部工具区，见 `web/components/zen-editor-view.tsx:34`

## 后端接口 / Service / Repository 链路

导出接口挂在项目路由上：`api/app/api/routes/projects.py:139`。

路由层只做四件事：

1. 读取项目
2. 读取该项目所有章节
3. 校验 `format` 是否为 `txt` 或 `epub`
4. 调用 `ExportService.build_export_response()`

具体拼装逻辑都在 `api/app/services/export.py:13`：

- `generate_txt_export()` 生成纯文本，见 `api/app/services/export.py:15`
- `generate_epub_export()` 用 `ebooklib` 生成电子书，见 `api/app/services/export.py:32`
- `build_export_response()` 负责媒体类型和下载文件名，见 `api/app/services/export.py:84`

## 数据模型

导出不引入新表，只读取已有的：

- `Project`：提供项目名
- `ProjectChapter`：提供按卷按章排序的标题与正文

因此导出永远反映的是“数据库里已经保存的章节内容”，而不是“编辑器当前 textarea 尚未保存的临时状态”。

## Prompt / LLM 调用要点

这是一条纯本地链路，不调用任何 LLM。它的约束来自格式而不是 Prompt：

- TXT 版保留卷标题与章节标题，用最朴素的纯文本拼接
- EPUB 版把每章正文按段落拆成 `<p>`，并生成目录结构

如果用户说“导出内容不对”，应先确认是否已保存当前章节，而不是先查模型行为。

## 关键文件索引

- `web/components/export-project-dialog.tsx`
- `web/components/projects-page-view.tsx`
- `web/components/zen-editor-view.tsx`
- `api/app/api/routes/projects.py`
- `api/app/services/export.py`
- `api/app/services/project_chapters.py`
- `api/app/db/models.py`

## 相关章节

- [20 项目](./20-projects.md) — 项目列表里的导出入口
- [22 Zen Editor](./22-zen-editor.md) — 编辑器中的导出入口
- [21 章节树](./21-chapter-tree.md) — 导出内容来自 `project_chapters`
- [40 本地开发与 Makefile](../40-operations/40-local-dev-and-make.md) — 下载文件后的本地验证方式
