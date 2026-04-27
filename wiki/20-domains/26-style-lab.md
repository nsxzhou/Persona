# 26 Style Lab：文风实验室

## 一句话定义 + 价值

Style Lab 是 Persona 的风格资产生产线。它把单个 TXT 样本转成两份可长期复用的 Markdown 资产：分析报告、Voice Profile，并最终保存为可挂载到项目上的 Style Profile。

## 用户视角流程

1. 用户进入 `/style-lab`，查看任务看板。
2. 点击“新建分析任务”，填写风格名称、Provider、模型覆盖并上传 TXT 样本。
3. 任务创建后立即跳转到 `/style-lab/:id` 的三步 Wizard。
4. 任务运行期间，用户可查看增量日志、暂停或恢复。
5. 任务成功后，依次浏览“分析报告 -> Voice Profile”，最后保存成 Style Profile，并可选择顺手挂载到某个项目。

## 前端入口与组件链路

Dashboard 页面在 `web/app/(workspace)/style-lab/page.tsx:45`：

- 用 React Query 拉取 Provider 列表和任务列表
- 卡片展示任务状态、当前阶段、样本文件与模型
- 支持直接删除任务

创建任务弹窗在 `web/components/style-lab-new-task-dialog.tsx:55`：

- 表单校验 TXT 文件与 Provider 选择
- 成功后跳到 `router.push(/style-lab/${newJob.id})`

Wizard 主体在 `web/components/style-lab-wizard-view.tsx:18`，它把流程切成两步：

- Step 1：分析报告
- Step 2：Voice Profile + 保存

状态管理主要落在 `web/hooks/use-style-lab-wizard-logic.ts:169`：

- 轮询 job status
- 增量拉取 execution logs
- 根据任务状态和是否已有 profile，动态决定展示“继续分析”还是“已保存档案”

任务成功并已保存后，页面会切换成 `web/components/style-lab-profile-view.tsx:17` 的档案视图。

## 后端接口 / Service / Repository 链路

任务 API 在 `api/app/api/routes/style_analysis_jobs.py`：

- 列表：`api/app/api/routes/style_analysis_jobs.py:26`
- 详情：`api/app/api/routes/style_analysis_jobs.py:42`
- 状态：`api/app/api/routes/style_analysis_jobs.py:57`
- 恢复 / 暂停：`api/app/api/routes/style_analysis_jobs.py:70` 与 `api/app/api/routes/style_analysis_jobs.py:83`
- 创建任务：`api/app/api/routes/style_analysis_jobs.py:97`
- 日志与各阶段产物：`api/app/api/routes/style_analysis_jobs.py:123`、`152`、`166`、`180`

任务业务 Service 在 `api/app/services/style_analysis_jobs.py:63`：

- `create()` 负责保存样本文件、创建 `style_sample_files` 和 `style_analysis_jobs`
- `resume()` / `pause()` 负责状态机切换，见 `api/app/services/style_analysis_jobs.py:180` 与 `205`
- `get_*_or_409()` 家族只允许在任务成功后读取报告与 Voice Profile，见 `api/app/services/style_analysis_jobs.py:271`

风格档案 API 则独立在 `api/app/api/routes/style_profiles.py` 与 `api/app/services/style_profiles.py`：

- `create()` 会从成功任务里拷贝报告，并写入可编辑Voice Profile，见 `api/app/services/style_profiles.py:64`
- `update()` 允许后续继续改风格名、Voice Profile，见 `api/app/services/style_profiles.py:112`
- `mount_project_id` 可在保存时顺手把档案挂到项目上，见 `api/app/services/style_profiles.py:44`

## 数据模型

Style Lab 横跨三张主表：

- `api/app/db/models.py:210` 的 `StyleSampleFile`：原始 TXT 的元信息
- `api/app/db/models.py:228` 的 `StyleAnalysisJob`：分析任务、阶段、日志与阶段产物
- `api/app/db/models.py:312` 的 `StyleProfile`：长期复用的风格档案

它们的关系是：

- 一个样本文件最多对应一个分析任务
- 一个成功任务最多保存成一个 Style Profile
- 一个 Style Profile 可被多个项目挂载

## Prompt / LLM 调用要点

Style Lab 不是一次 LLM 调用，而是多阶段流水线：

- 输入判定与切片
- 分块分析
- Reduce 聚合
- 报告整理
- Voice Profile 生成

Prompt 模板的实际实现位于 `api/app/prompts/style_analysis.py`；流水线直接导入这些 builder：

- `build_chunk_analysis_prompt()`
- `build_merge_prompt()`
- `build_report_prompt()`
- `build_voice_profile_prompt()`

其中 `build_voice_profile_prompt()` 的目标不是复述样本设定，而是产出可跨作品复用的风格执行资产：样本人物名、地名、势力名、事件名与专属设定词需要在这一层被去样本化，改写成角色原型、冲突原型与语义类别。
对于样本里极强的风格锚点，例如固定叙事人称、特定题材语境或高频思维模板，这一层只能把它们写成“优先采用的偏好”，不能直接升级成所有挂载项目都必须遵守的硬约束。

同时，阶段产物类型和状态常量由 `api/app/schemas/style_analysis_jobs.py:11`、`68`、`93` 定义，保证 Prompt 输出和持久化字段彼此对齐。

## 关键文件索引

- `web/app/(workspace)/style-lab/page.tsx`
- `web/app/(workspace)/style-lab/[id]/page.tsx`
- `web/components/style-lab-new-task-dialog.tsx`
- `web/components/style-lab-wizard-view.tsx`
- `web/components/style-lab-profile-view.tsx`
- `web/hooks/use-style-lab-wizard-logic.ts`
- `api/app/api/routes/style_analysis_jobs.py`
- `api/app/services/style_analysis_jobs.py`
- `api/app/api/routes/style_profiles.py`
- `api/app/services/style_profiles.py`
- `api/app/prompts/style_analysis.py`
- `api/app/db/models.py`

## 相关章节

- [15 LLM Provider 接入](../10-architecture/15-llm-provider-integration.md) — 任务如何选择 Provider 与模型
- [27 Style Analysis 管道](./27-style-analysis-pipeline.md) — 后台 LangGraph 流水线细节
- [30 Prompt 语料总览](../30-prompt-engineering/30-prompt-overview.md) — 通用 prompt 语料与生产分析 Prompt 的区别
