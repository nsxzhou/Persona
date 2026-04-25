# 20 项目（Project）

## 一句话定义 + 价值

Project 是 Persona 的业务根对象。它把“默认 Provider、可选 Style / Plot Profile、Project Bible 与章节树入口”收拢成一个可持续迭代的创作容器。

## 用户视角流程

1. 用户进入 `/projects` 查看所有项目，支持分页与“显示已归档”过滤。
2. 点击“新建项目”进入概念抽卡或项目创建入口。
3. 创建后进入项目详情页，在工作台内编辑描述、Bible 字段、默认 Provider、默认模型，以及挂载的 Style / Plot Profile。
4. 从项目卡片可以直接开始写作、导出、归档或恢复。

## 前端入口与组件链路

项目列表页入口是 `web/app/(workspace)/projects/page.tsx:1`，核心组件在 `web/components/projects-page-view.tsx:41`：

- React Query 负责分页拉取与缓存列表
- 卡片右侧直接暴露“导出 / 归档 / 开始写作 / 查看详情”
- 已归档项目切换为“恢复 / 永久删除”动作

项目配置表单在 `web/components/project-form.tsx:41`：

- 表单字段只覆盖项目元信息和依赖关系，不编辑正文
- 默认 Provider 通过可搜索的 Popover 选择，见 `web/components/project-form.tsx:128`
- 风格档案通过 Select 挂载，见 `web/components/project-form.tsx:184`
- 创建/更新最终分别走 `createProjectAction` 与 `updateProjectAction`，见 `web/components/project-form.tsx:27` 与 `web/components/project-form.tsx:236`

项目详情页本身是一个 Server Component：`web/app/(workspace)/projects/[id]/page.tsx`。它会先在服务端并发拉取：

- 项目本体
- Project Bible
- Provider 列表
- Style Profile 列表
- Plot Profile 列表

然后把这些数据一次性喂给 `ProjectWorkbench`。工作台内部由 `web/components/workbench-tabs.tsx` 管理 `description / world_building / characters / outline_master / outline_detail / runtime_state / runtime_threads / settings` 等标签页，并在同一 UI 下承接 Bible 编辑、大纲生成与设置修改。

## 后端接口 / Service / Repository 链路

HTTP 路由集中在 `api/app/api/routes/projects.py`：

- 项目 CRUD：`list_projects()` / `create_project()` / `get_project()` / `update_project()`
- Bible 读取与更新：`get_project_bible()` / `update_project_bible()`
- 归档 / 恢复 / 删除：`archive_project()` / `restore_project()` / `delete_project()`

Service 层在 `api/app/services/projects.py`：

- `create()` 会先校验默认 Provider 已启用，并按需校验 `style_profile_id` 与 `plot_profile_id`，见 `ProjectService.create()`
- `update()` 会处理 Provider 切换、模型兜底、Style / Plot Profile 重挂载与可编辑字段白名单，见 `ProjectService.update()`
- `get_bible_or_404()` / `update_bible()` 负责 `project_bibles` 的读取与落库
- `archive()` / `restore()` 只是切 `archived_at`，并没有独立归档表，见 `api/app/services/projects.py:151`

Repository 层在 `api/app/db/repositories/projects.py`：

- `list_summaries()` 会对列表页跳过大 Text 字段，只加载摘要列，见 `api/app/db/repositories/projects.py:27`
- `get_by_id()` 会预加载 `provider`，保证详情页和编辑器读取默认 Provider 不会触发懒加载，见 `api/app/db/repositories/projects.py:77`

## 数据模型

核心表是 `api/app/db/models.py` 中的 `Project`：

- 元数据：`name`、`description`、`status`、`archived_at`
- 依赖关系：`default_provider_id`、`default_model`、`style_profile_id`、`plot_profile_id`
- 偏好：`length_preset`、`auto_sync_memory`

围绕它的直接关系有两条：

- `projects.default_provider_id -> provider_configs.id`
- `projects.style_profile_id -> style_profiles.id`
- `projects.plot_profile_id -> plot_profiles.id`

项目本身不存 Bible 字段和章节正文：Bible 落在 `project_bibles`，正文落在 `project_chapters`。

## Prompt / LLM 调用要点

项目 CRUD 本身不直接调用 LLM，但它决定了后续所有 AI 能力的运行参数：

- `default_provider_id` 和 `default_model` 是编辑器、节拍、大纲生成与 Style Lab 之外的一切写作默认入口
- `style_profile_id` 决定 Voice Profile 是否会被注入到写作系统提示词中
- `plot_profile_id` 决定 Story Engine 是否会被注入到规划和写作链路中
- `length_preset` 会影响大纲、节拍和续写时的篇幅感知，见 `api/app/services/context_assembly.py:49`

换句话说，Project 不是“纯表单对象”，它是后续 Prompt 组装的主配置源。

## 关键文件索引

- `web/app/(workspace)/projects/page.tsx`
- `web/app/(workspace)/projects/[id]/page.tsx`
- `web/components/projects-page-view.tsx`
- `web/components/project-form.tsx`
- `api/app/api/routes/projects.py`
- `api/app/services/projects.py`
- `api/app/db/repositories/projects.py`
- `api/app/db/models.py`

## 相关章节

- [13 数据模型](../10-architecture/13-data-model.md) — `projects` 表的全量字段
- [15 LLM Provider 接入](../10-architecture/15-llm-provider-integration.md) — 默认 Provider 的来源
- [21 章节树](./21-chapter-tree.md) — 项目与章节的关系
- [22 Zen Editor](./22-zen-editor.md) — 项目在编辑器中的使用方式
- [26 Style Lab](./26-style-lab.md) — Style Profile 如何保存并回挂到项目
- [31 项目导出](./31-export.md) — 项目级导出入口
