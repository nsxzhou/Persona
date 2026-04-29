# 19 Novel Workflow 创作流引擎

> 本文档介绍了 Persona 平台的核心创作流系统（Novel Workflow）。该系统负责处理所有与创作相关的高时延异步 AI 任务。

## 要解决的问题

长篇创作不是一次简单的 LLM API 调用，而是一个复杂的工程。我们需要：
1. 处理多步骤、互相依赖的复杂生成流程（如：从大纲到节拍再到正文）。
2. 在长流程中支持暂停、恢复以及人工介入（Human-in-the-Loop）。
3. 解决不同意图下（如生成设定、刷新记忆、扩写正文）的上下文精准组装问题。
4. 为前端提供状态轮询或流式更新（SSE Streaming）。

## 关键概念与核心机制

### 1. 核心引擎（LangGraph）

Novel Workflow 底层使用 [LangGraph](https://python.langchain.com/v0.1/docs/langgraph/) 构建状态机管道（`NovelWorkflowPipeline`）。
- **State**：定义了 `NovelWorkflowState`，其中包含了 `run_id`, `intent_type` 以及各种运行时的中间产物。
- **Memory/Checkpointer**：使用 `InMemorySaver` 或持久化的 checkpointer 管理任务级别的状态图，支持在特定节点打断与恢复。

### 2. Intent Routing（意图路由）

根据任务类型的不同，工作流会路由到不同的处理节点（Intent Handlers）：
- `concept_bootstrap`：概念抽卡，生成创意设定。
- `section_generate`：生成/重写特定设定。
- `volume_generate` / `volume_chapters_generate`：卷纲与章节大纲生成。
- `beats_generate` / `beat_expand`：节拍生成与正文扩写。
- `memory_refresh`：记忆刷新，同步角色状态与运行时线程。

### 3. Context Assembly（上下文组装）

长篇创作对 Context 极度敏感。工作流在执行前，会通过 Context 组装服务（如 `WritingContextSections` 等）拼接精准的上下文：
- **Voice Profile**：文风配置。
- **Story Engine**：情节引擎配置。
- **Current Bible**：当前圣经数据（世界观、角色状态、运行时状态）。
- **Objective Card**：章节目标卡。
- 根据意图不同，动态注入前序章节内容、当前光标前文本等。

### 4. 状态与生命周期（State & Lifecycle）

任务具有完整的异步生命周期，由后端的 Worker (`NovelWorkflowJobExecutor`) 处理。
- **状态流转**：`pending` -> `running` -> `succeeded` / `failed`。
- **暂停与恢复**（Pause / Resume）：
  - 用户可以主动请求暂停，更新 `pause_requested_at`。
  - Worker 在 `llm_complete` 调用前或节点边界检查打断信号。
  - 任务转入 `paused` 状态后，前端可调用 `/resume` 恢复执行，系统重置为 `pending`，由 Worker 再次拾取。

### 5. 人工介入（Human-in-the-Loop）

复杂流中可以设置明确的检查点（`checkpoint_kind`）。
- 抛出 `NovelWorkflowAwaitingHuman` 异常主动中断流程。
- 任务进入 `paused` 状态，等待用户通过 `/decision` 接口提交决策（如修改并确认生成的大纲 Bundle）。
- 提交决策后，工作流带着用户的修改结果重新入队，继续向下执行。

### 6. SSE Streaming 与日志

在长耗时生成过程中，为了避免用户焦虑，需要将中间状态实时透传：
- **Job Logs**：Worker 会不断通过 Storage Service 追加执行日志（如 `[Workflow] starting...`）。
- **SSE Streaming**：结合 `16-sse-and-streaming.md` 中的设计，前端可以通过 SSE (Server-Sent Events) 或长轮询端点实时监听生成过程中的进度、状态变更及日志增量。虽然部分日志通过 offset 轮询获取，但在架构上，SSE 是支持大段文本流式生成及进度推送的核心通信方式。

## 核心模型与文件索引

### 数据模型
- `NovelWorkflowRun`：记录工作流任务实例的状态、进度及关联的 Payload。

### 后端链路
- `api/app/api/routes/novel_workflows.py`：API 路由，提供创建、查询、暂停、恢复、提交决策及获取日志的接口。
- `api/app/services/novel_workflows.py`：服务层，处理状态机业务逻辑、任务调度与数据库操作。
- `api/app/services/novel_workflow_worker.py`：异步 Worker，负责拉取并执行任务，处理 Heartbeat。
- `api/app/services/novel_workflow_pipeline.py`：LangGraph 状态机定义、节点逻辑、Intent Handler 实现。
- `api/app/services/context_assembly.py`：上下文组装逻辑核心实现。
