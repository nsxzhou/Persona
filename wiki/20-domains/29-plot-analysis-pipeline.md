# 29 Plot Analysis 管道（LangGraph）

## 一句话定义 + 价值

这是 Persona 体量第二大的后台子系统：一个由 Worker 驱动、由 LangGraph 编排、支持 checkpoint、断点续跑、暂停恢复和任务租约的长文本情节分析流水线。

Plot 分析相对于 [Style 分析](./27-style-analysis-pipeline.md) 的关键架构差异是：它先跑一次 **sketch → skeleton** 全局预览，再让所有下游阶段消费这份 ≤2500 tokens 的全书骨架。原因是情节维度（阶段划分、主爽点兑现节奏、主角能力走向、关系演变、结局形状）几乎都需要**全书视角**才能稳定产出；而文风维度是 chunk-local 的，所以 Style 分析不需要这个预览层。

> 当前仓库状态下，Plot 分析执行器已经接入默认后台入口：`api/app/worker.py` 会在同一进程内并发运行 Style 与 Plot 两条 worker 循环，所以 `make dev` 下的 Plot 任务会被自动消费。

## 用户视角流程

1. 用户在 Plot Lab 上传 TXT 并创建任务。
2. 任务先进入 `pending`，随后被默认后台 Worker claim。
3. Worker 先切片并判定文本类型，**再并行生成每个 chunk 的 sketch JSON**，聚合成全书骨架 Markdown。
4. Worker 继续驱动 LangGraph 把骨架注入到后续的分块分析、Reduce、报告整理阶段。
5. 前端 Wizard 轮询状态、拉取日志，并在成功后依次读取报告 / 骨架 / Story Engine。
6. 用户确认后把结果保存成 Plot Profile。

## 前端入口与组件链路

这个子系统没有独立的“管道页面”，它通过 Plot Lab Wizard 侧向暴露：

- `web/components/plot-lab-wizard-view.tsx:19` 决定当前展示的 step（报告 / 骨架 / Story Engine）
- `web/components/plot-lab-wizard-skeleton-step.tsx:10` 是骨架审阅面板（skeleton-only，由 Wizard Step 2 渲染）
- `web/components/plot-lab-wizard-report-step.tsx:16` 在运行期显示日志与阶段状态
- `web/hooks/use-plot-lab-wizard-logic.ts:83` 轮询 status（2s）
- `web/hooks/use-plot-lab-wizard-logic.ts:98` 增量拉取 execution logs（1s，64KiB 滑窗）
- `web/hooks/use-plot-lab-wizard-logic.ts:129` 汇总 report / summary / **skeleton** / prompt pack 的加载，只有任务成功且尚未保存为 Profile 时才启用

前端只负责观察 job status 与读取阶段产物，真正的状态机全部在后端。

## 后端接口 / Service / Repository 链路

### 任务与产物 API

前端主要消费这些只读接口（定义见 `api/app/api/routes/plot_analysis_jobs.py`）：

- `GET /plot-analysis-jobs/{id}/status`，见 `api/app/api/routes/plot_analysis_jobs.py:60`
- `GET /plot-analysis-jobs/{id}/logs`，见 `api/app/api/routes/plot_analysis_jobs.py:129`
- `GET /plot-analysis-jobs/{id}/analysis-meta`，见 `api/app/api/routes/plot_analysis_jobs.py:145`
- `GET /plot-analysis-jobs/{id}/analysis-report`，见 `api/app/api/routes/plot_analysis_jobs.py:159`
- `GET /plot-analysis-jobs/{id}/plot-summary`，见 `api/app/api/routes/plot_analysis_jobs.py:173`
- `GET /plot-analysis-jobs/{id}/prompt-pack`，见 `api/app/api/routes/plot_analysis_jobs.py:187`
- `GET /plot-analysis-jobs/{id}/plot-skeleton`，见 `api/app/api/routes/plot_analysis_jobs.py:201`（骨架专属端点）

### LangGraph 主图

`api/app/services/plot_analysis_pipeline.py:104` 的 `PlotAnalysisPipeline` 是主图实现。图节点以 `_build_graph()`（`api/app/services/plot_analysis_pipeline.py:176`）的添加顺序为准：

- `prepare_input`，见 `api/app/services/plot_analysis_pipeline.py:202`
- `_route_sketches`（路由函数），见 `api/app/services/plot_analysis_pipeline.py:214`
- `sketch_chunk`（**新节点**：并行生成 per-chunk sketch JSON），见 `api/app/services/plot_analysis_pipeline.py:234`
- `build_skeleton`（**新节点**：sketch → 骨架 Markdown 的 reduce），见 `api/app/services/plot_analysis_pipeline.py:289`
  - 分层归约兜底 `_build_skeleton_hierarchical()`，见 `api/app/services/plot_analysis_pipeline.py:334`
  - 触发阈值常量 `SKELETON_HIERARCHICAL_TOKEN_THRESHOLD = 80_000`（`api/app/services/plot_analysis_pipeline.py:47`）与 `SKELETON_GROUP_SIZE = 40`（`api/app/services/plot_analysis_pipeline.py:50`），均 module-level 便于测试 monkeypatch
- `_route_chunks`（路由函数，要求骨架已写入 state），见 `api/app/services/plot_analysis_pipeline.py:388`
- `analyze_chunk`（骨架感知），见 `api/app/services/plot_analysis_pipeline.py:415`
- `merge_chunks`（骨架感知），见 `api/app/services/plot_analysis_pipeline.py:455`
- `build_report`（骨架感知），见 `api/app/services/plot_analysis_pipeline.py:521`
- `build_summary`，见 `api/app/services/plot_analysis_pipeline.py:544`
- `build_prompt_pack`，见 `api/app/services/plot_analysis_pipeline.py:566`
- `persist_result`，见 `api/app/services/plot_analysis_pipeline.py:588`

`thread_id = job_id` 被写进 LangGraph config（`api/app/services/plot_analysis_pipeline.py:159`），保证 checkpoint 寻址键与业务任务键完全一致；`max_concurrency` 也在同一处下发（`:160`）。

### Worker 执行壳

`api/app/services/plot_analysis_worker.py` 负责把“业务任务”包装成“可重复执行的后台作业”，结构与 Style 分析几乎完全对称：

- `process_next_pending()`，见 `api/app/services/plot_analysis_worker.py:50`
- `_claim_next_pending_job()`，见 `api/app/services/plot_analysis_worker.py:61`
- `_run_claimed_job()`（真正执行核心），见 `api/app/services/plot_analysis_worker.py:76`
- `_load_run_context()`（切片 + 分类，支持复用已存在的切片 artifact），见 `api/app/services/plot_analysis_worker.py:184`
- `_run_stage_heartbeat_loop()`，见 `api/app/services/plot_analysis_worker.py:155`
- `fail_stale_running_jobs()`（由 API lifespan 调用，恢复陈旧任务），见 `api/app/services/plot_analysis_worker.py:342`
- `run_worker()`（长轮询循环），见 `api/app/services/plot_analysis_worker.py:356`

当前默认运行路径下，Plot 执行循环已经接入统一后台入口：

- `api/app/main.py` 在 lifespan 里调用 Plot 的 `fail_stale_running_jobs()`
- `api/app/services/plot_analysis_worker.py` 负责 Plot 的完整执行循环
- `api/app/worker.py` 会并发启动 Style 与 Plot 两条 `run_worker()`
- `Makefile` 的 `make worker` / `make dev` 会拉起这一统一后台进程

Plot Worker 直接复用 Style 侧的共享组件：

- Checkpointer 工厂 `api/app/services/plot_analysis_checkpointer.py:9` 直接继承 `StyleAnalysisCheckpointerFactory`
- `read_chunks_and_classification()` 与编码探测 / 切片 / 分类都在 `api/app/services/style_analysis_text.py`
- LLM 客户端与重试均使用 `api/app/services/style_analysis_llm.py:87` 的 `MarkdownLLMClient`

### Checkpointer 与落盘产物

- Checkpointer 工厂在 `api/app/services/plot_analysis_checkpointer.py:9`（继承自 style）
- 样本、chunk、**sketch**、chunk-analysis、阶段 Markdown、JSON 分类结果和日志都由 `api/app/services/plot_analysis_storage.py:17` 的 `PlotAnalysisStorageService` 管理：
  - 根目录按 `plot-samples/` 与 `plot-analysis-artifacts/<job_id>/` 分离（`api/app/services/plot_analysis_storage.py:21`、`24`）
  - Sketch artifact 读写 `write_sketch_artifact()` / `sketch_artifact_exists()` / `read_all_sketches()`，见 `api/app/services/plot_analysis_storage.py:134`、`151`、`175`，以 `sketches/{chunk_index:06d}.json` 原子写落盘
  - Stage Markdown（包括 `plot-skeleton.md`）由 `write_stage_markdown_artifact()` 管理，见 `api/app/services/plot_analysis_storage.py:188`
- 任务日志的增量读取在 `api/app/services/plot_analysis_storage.py:251`

## 数据模型

这个领域最依赖 `PlotAnalysisJob`，定义在 `api/app/db/models.py:379`。关键字段：

- 身份与来源：`plot_name`、`provider_id`、`model_name`、`sample_file_id`
- 状态机：`status`、`stage`（`api/app/db/models.py:414`、`417`）
- 故障恢复：`attempt_count`、`locked_by`、`locked_at`、`last_heartbeat_at`、`pause_requested_at`、`paused_at`
- 结果载荷（5 个）：`analysis_meta_payload`、`analysis_report_payload`、`plot_summary_payload`、`prompt_pack_payload`、**`plot_skeleton_payload`**（`api/app/db/models.py:423`，由 `0013_plot_skeleton_payload` 新增）
- 生命周期：`started_at`、`completed_at`

`PlotProfile`（`api/app/db/models.py:461`）镜像其中 4 份 Markdown 资产，骨架字段在 `api/app/db/models.py:480`。

状态常量与 stage 常量定义在 `api/app/schemas/plot_analysis_jobs.py`。当前执行顺序如下：

1. `preparing_input`
2. `building_skeleton`（sketch fan-out + skeleton reduce 都归到这个 stage 标签下）
3. `selecting_focus_chunks`
4. `analyzing_focus_chunks`
5. `aggregating`
6. `reporting`
7. `postprocessing`

## Prompt / LLM 调用要点

### 分析 Prompt 全是 Markdown-First，唯一例外是 sketch

模板实际实现集中在 `api/app/prompts/plot_analysis.py`；`api/app/services/plot_analysis_prompts.py` 只是流水线导入用的兼容层：

- `SHARED_ANALYSIS_RULES` 强制证据优先、中文 Markdown、章节顺序固定
- `SKETCH_ANALYSIS_RULES` 是**唯一一处本地反转**：sketch 必须输出合法 JSON 以便下游聚合，显式禁止 Markdown 与代码块
- `PLOT_ANALYSIS_REPORT_SECTIONS` 定义固定的 3.1-3.12 共 12 节结构，见 `api/app/schemas/plot_analysis_jobs.py:11`
- `PLOT_REPORT_TEMPLATE` / `PLOT_SUMMARY_TEMPLATE` / `PLOT_PROMPT_PACK_TEMPLATE` / `PLOT_SKELETON_TEMPLATE` 把最终输出格式全部锁死

### 8 个 Builder 与骨架注入

| Builder | 定义位置 | 阶段 | 骨架参数 |
| --- | --- | --- | --- |
| `build_sketch_prompt()` | `api/app/prompts/plot_analysis.py` | sketch_chunk | — |
| `build_skeleton_reduce_prompt()` | `api/app/prompts/plot_analysis.py` | build_skeleton | — |
| `build_skeleton_group_reduce_prompt()` | `api/app/prompts/plot_analysis.py` | build_skeleton（分层兜底） | — |
| `build_chunk_analysis_prompt()` | `api/app/prompts/plot_analysis.py` | analyze_chunk | `plot_skeleton: str \| None` |
| `build_merge_prompt()` | `api/app/prompts/plot_analysis.py` | merge_chunks | `plot_skeleton: str \| None` |
| `build_report_prompt()` | `api/app/prompts/plot_analysis.py` | build_report | `plot_skeleton: str \| None` |
| `build_plot_summary_prompt()` | `api/app/prompts/plot_analysis.py` | build_summary | — |
| `build_prompt_pack_prompt()` | `api/app/prompts/plot_analysis.py` | build_prompt_pack | — |

骨架注入由 `_format_skeleton_context()`（定义在 `api/app/prompts/plot_analysis.py`）统一拼接：在主输入前插入一节 `## 全书骨架（参考上下文）`，并附加反伪造声明“骨架仅用于定位与上下文参考；所有结论仍须以本 chunk 证据为准，不得引用骨架外的事件”。

`build_report_prompt()` 在骨架存在时还会额外提示“3.1 阶段划分、3.2 主爽点线兑现节奏、3.11 结局形状应优先参考骨架的阶段与节奏判断”。

### ≤2500 tokens 的骨架硬约束

`build_skeleton_reduce_prompt()` 明确要求“整份骨架合计不得超过约 2500 tokens”，这是为了让骨架可以整段注入到每个下游 chunk prompt 而不爆上下文。输出模板固定在 `PLOT_SKELETON_TEMPLATE`：阶段划分 / 主线推进链 / 爽点兑现节奏 / 角色登场 & 主角能力阶梯 / 时间线结构 / 结局形状线索 / 证据不足项。

### 分层归约兜底

当 sketch 规模的估算 token 数超过 `SKELETON_HIERARCHICAL_TOKEN_THRESHOLD = 80_000`（定义在 `api/app/services/plot_analysis_pipeline.py`），`_build_skeleton()` 会走 `_build_skeleton_hierarchical()`：把 sketches 按 `SKELETON_GROUP_SIZE = 40` 分组，先生成一批 sub-skeleton Markdown，再由 `build_skeleton_reduce_prompt()` 做二次归约。`build_skeleton_reduce_prompt()` 显式兼容两种输入形状（sketch JSON 或 sub-skeleton 对象）。

### LLM 调用复用 Style 侧

`api/app/services/style_analysis_llm.py:87` 的 `MarkdownLLMClient`（`temperature=0.0`、空响应重试、从多个位置兜底提取正文）被 Plot 流水线原样复用。

### 输入判定在 Worker 前置

`api/app/services/style_analysis_text.py:119` 的 `read_chunks_and_classification()` 在真正跑图前完成编码探测、文本清洗、chunk 切分与输入分类（章节正文 / 口语字幕 / 混合文本）。这些 classification 结果会直接注入到 sketch / 分析 / Reduce / 报告四条 prompt 里。

## LangGraph 流程图

```mermaid
flowchart TD
    Upload["上传 TXT"] --> Job["plot_analysis_jobs.status=pending"]
    Job --> Claim["Worker claim + lease"]
    Claim --> Prepare["prepare_input"]
    Prepare --> RouteSketch["route_sketches"]
    RouteSketch --> SketchN["sketch_chunk #1..N（并行）"]
    SketchN --> Skeleton["build_skeleton（含分层归约兜底）"]
    Skeleton --> RouteChunk["route_chunks"]
    RouteChunk --> AnalyzeN["analyze_chunk #1..N（骨架感知）"]
    AnalyzeN --> Merge["merge_chunks（骨架感知）"]
    Merge --> Report["build_report（骨架感知）"]
    Report --> Summary["build_summary"]
    Summary --> Pack["build_prompt_pack"]
    Pack --> Persist["persist_result"]
    Persist --> Success["status=succeeded"]

    Claim -. pause_requested_at .-> Pause["status=paused"]
    Claim -. stale heartbeat .-> Requeue["fail_stale_running_jobs -> pending"]
    Skeleton -. plot-skeleton.md / sketches/*.json .-> Resume["按 job_id 续跑时跳过已完成的 sketch 与骨架"]
```

## 关键文件索引

- `api/app/services/plot_analysis_pipeline.py`
- `api/app/services/plot_analysis_worker.py`
- `api/app/prompts/plot_analysis.py`
- `api/app/services/plot_analysis_storage.py`（包含 sketch artifact 读写与 stage markdown helper）
- `api/app/services/plot_analysis_checkpointer.py`
- `api/app/services/plot_analysis_jobs.py`
- `api/app/api/routes/plot_analysis_jobs.py`
- `api/app/schemas/plot_analysis_jobs.py`
- `api/app/services/style_analysis_llm.py`（共享 LLM 客户端）
- `api/app/services/style_analysis_text.py`（共享 chunking + classification）
- `api/alembic/versions/0012_plot_lab.py`（Plot Lab 初始表）
- `api/alembic/versions/0013_plot_skeleton_payload.py`（骨架列迁移）
- `api/app/worker.py`（统一后台入口，并发运行 Style + Plot 两条 worker 循环）
- `web/hooks/use-plot-lab-wizard-logic.ts`
- `web/components/plot-lab-wizard-skeleton-step.tsx`
- `web/components/plot-lab-wizard-report-step.tsx`

## 相关章节

- [10 整体架构总图](../10-architecture/10-high-level-architecture.md) — Worker 与 API 的角色分工
- [11 后端分层](../10-architecture/11-backend-layering.md) — Worker 的事务与 Service 组织方式
- [13 数据模型](../10-architecture/13-data-model.md) — `plot_analysis_jobs` / `plot_profiles`
- [27 Style Analysis 管道](./27-style-analysis-pipeline.md) — 同构但无骨架前置的姊妹管道
- [28 Plot Lab](./28-plot-lab.md) — 管道在产品流程中的外观
- [30 Prompt 语料总览](../30-prompt-engineering/30-prompt-overview.md) — 通用 prompt 语料与生产分析 Prompt 的边界
- [32 ANALYZE-GENERATE 手法论](../30-prompt-engineering/32-analyze-generate-playbook.md) — 分析输出如何转成生成资产
