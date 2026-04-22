# 28 Plot Lab：情节实验室

## 一句话定义 + 价值

Plot Lab 是 Persona 的情节资产生产线。它接收单个 TXT 样本，输出四份可长期复用的 Markdown 资产：**全书骨架、分析报告、情节摘要、Plot Prompt Pack**，并最终保存为可挂载到项目上的 Plot Profile。与 Style Lab 关注“怎么写”不同，Plot Lab 关注的是“讲什么、怎么推进、怎么兑现爽点”。

> 当前仓库的默认后台入口 `api/app/worker.py` 已经会在同一进程内并发轮询 Style 与 Plot 两类任务；因此 `make dev` 下创建的 Plot Job 会被统一 Worker 自动消费。

## 用户视角流程

1. 用户进入 `/plot-lab`，查看情节分析任务看板。
2. 点击“新建分析任务”，填写情节档案名称、Provider、模型覆盖并上传 TXT 样本。
3. 任务创建后立即跳转到 `/plot-lab/:id` 的 **四步 Wizard**。
4. 任务运行期间，用户可查看增量日志、暂停或恢复。
5. 任务成功后，依次浏览 **分析报告 → 全书骨架 → 剧情摘要 → Plot Prompt**，最后保存成 Plot Profile，并可选择顺手挂载到某个项目。

骨架位于第二步，意图是让用户在读长篇报告之前先快速审阅一份 ≤2500 tokens 的全书视图，再进入更细的章节展开——这也是 Plot 分析与 Style 分析最直观的产品差异。

## 前端入口与组件链路

Dashboard 页面在 `web/app/(workspace)/plot-lab/page.tsx:46`：

- 用 React Query 拉取 Provider 列表和任务列表
- 卡片展示任务状态、当前阶段（通过 `formatPlotStageLabel` 渲染中文）、样本文件与模型
- 支持直接删除任务

创建任务弹窗在 `web/components/plot-lab-new-task-dialog.tsx:55`：

- 表单校验 TXT 文件与 Provider 选择
- 成功后跳到 `router.push(/plot-lab/${newJob.id})`

Wizard 主体在 `web/components/plot-lab-wizard-view.tsx:19`，它把流程切成四步：

- Step 1：分析报告（`PlotLabWizardReportStep`，`web/components/plot-lab-wizard-report-step.tsx:16`）
- Step 2：全书骨架（`PlotLabWizardSkeletonStep`，`web/components/plot-lab-wizard-skeleton-step.tsx:10`）
- Step 3：剧情摘要（`PlotLabWizardSummaryStep`，`web/components/plot-lab-wizard-summary-step.tsx`）
- Step 4：Plot Prompt + 保存（`PlotLabWizardPromptPackStep`，`web/components/plot-lab-wizard-prompt-pack-step.tsx`）

状态管理集中在 `web/hooks/use-plot-lab-wizard-logic.ts:395` 的 `usePlotLabWizardLogic()`：

- 轮询 job status（`web/hooks/use-plot-lab-wizard-logic.ts:83` 的 `usePlotLabJobStatusQuery`，`refetchInterval = 2s`）
- 增量拉取 execution logs（`web/hooks/use-plot-lab-wizard-logic.ts:98` 的 `usePlotLabJobLogsQuery`，`refetchInterval = 1s`，保留 64KiB 窗口）
- 延迟加载阶段产物：成功且未保存 Profile 时才请求 report / summary / skeleton / prompt pack（`web/hooks/use-plot-lab-wizard-logic.ts:129` 的 `usePlotLabResourcesQueries`）
- 当任务已保存为 Profile 时，优先用 Profile 数据填充，节省一次 API 调用（`web/hooks/use-plot-lab-wizard-logic.ts:169` 的 `mergeJobResources`）
- 根据任务状态和是否已有 profile，动态决定展示“继续分析”还是“已保存档案”

任务成功并已保存后，页面会切换成 `web/components/plot-lab-profile-view.tsx:17` 的档案视图，以 Tabs 呈现剧情摘要 / 提示词资产 / 原始分析报告。

## 后端接口 / Service / Repository 链路

任务 API 在 `api/app/api/routes/plot_analysis_jobs.py`：

- 列表：`api/app/api/routes/plot_analysis_jobs.py:28`
- 详情：`api/app/api/routes/plot_analysis_jobs.py:45`
- 状态：`api/app/api/routes/plot_analysis_jobs.py:60`
- 恢复 / 暂停：`api/app/api/routes/plot_analysis_jobs.py:74` 与 `api/app/api/routes/plot_analysis_jobs.py:88`
- 创建任务：`api/app/api/routes/plot_analysis_jobs.py:102`
- 日志与各阶段产物：`api/app/api/routes/plot_analysis_jobs.py:129`、`145`、`159`、`173`、`187`、`201`
  - 其中 `GET /plot-analysis-jobs/{id}/plot-skeleton` 在 `api/app/api/routes/plot_analysis_jobs.py:201` 是骨架专属的只读端点
- 删除任务：`api/app/api/routes/plot_analysis_jobs.py:215`

任务业务 Service 在 `api/app/services/plot_analysis_jobs.py:62` 的 `PlotAnalysisJobService`：

- `create()` 负责保存样本文件、创建 `plot_sample_files` 和 `plot_analysis_jobs`，见 `api/app/services/plot_analysis_jobs.py:466`
- `resume()` / `pause()` 负责状态机切换，见 `api/app/services/plot_analysis_jobs.py:179` 与 `204`
- `get_*_or_409()` 家族只允许在任务成功后读取报告、骨架、摘要与 Prompt Pack，见 `api/app/services/plot_analysis_jobs.py:286`、`302`、`318`、`334`
- `mark_job_succeeded()` 会一次性写入 5 个 payload（报告 / 摘要 / Prompt Pack / 骨架 / 元数据），见 `api/app/services/plot_analysis_jobs.py:397`

情节档案 API 则独立在 `api/app/api/routes/plot_profiles.py` 与 `api/app/services/plot_profiles.py`：

- `create()` 会从成功任务里拷贝报告与骨架，并写入可编辑摘要 / Prompt Pack，见 `api/app/services/plot_profiles.py:64`
- `update()` 允许后续继续改情节名、摘要、Prompt Pack 以及骨架（骨架非空时覆写），见 `api/app/services/plot_profiles.py:119`
- `mount_project_id` 可在保存时顺手把档案挂到项目上，见 `api/app/services/plot_profiles.py:44`

运行入口现在已经接好：`api/app/worker.py` 会并发启动 Style 与 Plot 两条轮询循环，因此本地默认环境里创建的 Plot Job 会由同一个后台进程直接推进，不再停在 `pending`。

## 数据模型

Plot Lab 横跨三张主表（均定义在 `api/app/db/models.py`）：

- `api/app/db/models.py:361` 的 `PlotSampleFile`：原始 TXT 的元信息（文件名、content type、存储路径、字节数、字符数、sha256）
- `api/app/db/models.py:379` 的 `PlotAnalysisJob`：分析任务、阶段、日志与阶段产物
  - 五个 payload 字段：`analysis_meta_payload`、`analysis_report_payload`、`plot_summary_payload`、`prompt_pack_payload`、`plot_skeleton_payload`
  - `plot_skeleton_payload` 位于 `api/app/db/models.py:423`，由 `0013_plot_skeleton_payload` 迁移引入
  - 故障恢复字段：`locked_by`、`locked_at`、`last_heartbeat_at`、`pause_requested_at`、`paused_at`、`attempt_count`
- `api/app/db/models.py:461` 的 `PlotProfile`：长期复用的情节档案
  - 四份资产镜像：`analysis_report_payload` / `plot_summary_payload` / `prompt_pack_payload` / `plot_skeleton_payload`（骨架字段在 `api/app/db/models.py:480`）
  - 通过 `source_job_id` 唯一绑定任务，通过 `projects` 反向关系允许多个项目挂载

它们的关系是：

- 一个样本文件最多对应一个分析任务（`sample_file_id` 唯一）
- 一个成功任务最多保存成一个 Plot Profile（`source_job_id` 唯一）
- 一个 Plot Profile 可被多个项目挂载

## Prompt / LLM 调用要点

Plot Lab 不是一次 LLM 调用，而是多阶段流水线，管道节点顺序固定：输入准备 → **分块速写（sketch）→ 全书骨架归约** → 分块分析（骨架感知）→ Reduce 聚合（骨架感知）→ 报告整理（骨架感知）→ 剧情摘要 → Plot Prompt Pack → 持久化。

`sketch → skeleton` 这一前置预览是 Plot Lab 相对 Style Lab 的核心架构差异：情节维度（阶段划分、主爽点兑现节奏、主角能力走向、关系演变、结局形状）几乎都需要全书视角，而文风是 chunk-local 的。

Prompt 模板与构造器都集中在 `api/app/services/plot_analysis_prompts.py`，核心 8 个 builder：

- `build_sketch_prompt()`（`:161`）——分块速写，**全文件唯一允许 JSON 输出的分支**，见模块里与 `SHARED_ANALYSIS_RULES` 并列的 `SKETCH_ANALYSIS_RULES`（`:21`）
- `build_skeleton_reduce_prompt()`（`:206`）——把 sketches 归约成 ≤2500 tokens 的 `plot-skeleton.md`
- `build_skeleton_group_reduce_prompt()`（`:237`）——分层归约兜底：当 sketch 规模超过 `SKELETON_HIERARCHICAL_TOKEN_THRESHOLD` 时先做 group reduce，再汇总
- `build_chunk_analysis_prompt()`（`:268`）——分块分析，接受 `plot_skeleton` 参数注入
- `build_merge_prompt()`（`:291`）——Reduce 聚合阶段
- `build_report_prompt()`（`:310`）——最终报告整理
- `build_plot_summary_prompt()`（`:334`）——剧情摘要
- `build_prompt_pack_prompt()`（`:349`）——Plot Prompt Pack

`_format_skeleton_context()`（`api/app/services/plot_analysis_prompts.py:35`）是三条下游 builder（chunk 分析 / merge / report）的共享拼接器，会在输入前注入一节 `## 全书骨架（参考上下文）` 并附带反伪造声明（“骨架仅用于定位与上下文参考；所有结论仍须以本 chunk 证据为准，不得引用骨架外的事件”）。

管道编排与阶段 / 状态常量定义在 `api/app/schemas/plot_analysis_jobs.py:119` 之后，报告结构 `PLOT_ANALYSIS_REPORT_SECTIONS` 锁定 3.1-3.12 共 12 个情节维度子标题。管道具体实现与节点拓扑见下一章 [29 Plot Analysis 管道（LangGraph）](./29-plot-analysis-pipeline.md)。

## 关键文件索引

- `web/app/(workspace)/plot-lab/page.tsx`
- `web/app/(workspace)/plot-lab/[id]/page.tsx`
- `web/components/plot-lab-new-task-dialog.tsx`
- `web/components/plot-lab-wizard-view.tsx`
- `web/components/plot-lab-wizard-report-step.tsx`
- `web/components/plot-lab-wizard-skeleton-step.tsx`
- `web/components/plot-lab-wizard-summary-step.tsx`
- `web/components/plot-lab-wizard-prompt-pack-step.tsx`
- `web/components/plot-lab-profile-view.tsx`
- `web/hooks/use-plot-lab-wizard-logic.ts`
- `api/app/api/routes/plot_analysis_jobs.py`
- `api/app/api/routes/plot_profiles.py`
- `api/app/services/plot_analysis_jobs.py`
- `api/app/services/plot_profiles.py`
- `api/app/services/plot_analysis_prompts.py`
- `api/app/db/models.py`（`PlotSampleFile` / `PlotAnalysisJob` / `PlotProfile`）

## 相关章节

- [15 LLM Provider 接入](../10-architecture/15-llm-provider-integration.md) — 任务如何选择 Provider 与模型
- [26 Style Lab](./26-style-lab.md) — 同构的文风资产生产线（无骨架前置）
- [29 Plot Analysis 管道](./29-plot-analysis-pipeline.md) — 后台 LangGraph 流水线细节
- [30 Prompt 语料总览](../30-prompt-engineering/30-prompt-overview.md) — 通用 prompt 语料与生产分析 Prompt 的区别
