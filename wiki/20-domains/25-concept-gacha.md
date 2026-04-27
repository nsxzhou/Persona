# 25 概念抽卡（Concept Gacha）

## 一句话定义 + 价值

Concept Gacha 是 Persona 的“新项目启动器”。它不是直接让用户填空创建项目，而是先让模型基于一段灵感生成 3 张差异化概念卡，再从中选一张落成真正的 Project。

## 用户视角流程

1. 用户进入 `/projects/new`。
2. 选择一个已启用的 Provider，可选填模型覆盖。
3. 输入灵感描述，点击“生成标题和简介”。
4. 页面展示 3 张概念卡，用户选择一张，并选定目标篇幅预设与可选风格档案。
5. 确认后系统立刻创建项目，并跳转到项目详情页。

## 前端入口与组件链路

页面入口在 `web/app/(workspace)/projects/new/page.tsx:4`。它先通过 `getServerApi()` 拉取 Provider 列表，再把数据交给 `ConceptGachaPage`。

核心交互都在 `web/components/concept-gacha-page.tsx:28`：

- `handleGenerate()` 负责调用 `api.generateConcepts()`，见 `web/components/concept-gacha-page.tsx:42`
- `handleConfirm()` 负责把被选中的概念转换成真正的 `ProjectCreate` payload，见 `web/components/concept-gacha-page.tsx:65`
- `lengthPreset` 选择器让项目从一开始就带上篇幅目标
- 页面还允许在创建前预挂风格档案与情节档案

这个页面有两个有意的产品选择：

- 概念卡固定一次给 3 张，鼓励用户在“方向差异”里做选择，而不是无限抽卡
- 创建项目时只写最少字段，其余 Bible 字段都留空，后续再逐步生成或人工完善

## 后端接口 / Service / Repository 链路

概念生成通过 novel workflow 创建 `concept_bootstrap` run，而不是挂在 projects router 上。

Service 链路在 `api/app/services/novel_workflows.py`、`api/app/services/novel_workflow_worker.py` 与 `api/app/services/novel_workflow_pipeline.py`：

- 先通过 `ProviderConfigService.ensure_enabled()` 校验 Provider 可用
- 再由 `ConceptAgent` 拼装概念生成 system prompt 与 user message
- 最后把 Markdown 产物写成 `concepts_markdown` artifact

前端在 `web/lib/api-client.ts` 中把 `concepts_markdown` 解析成概念卡：

- 约定模型输出形如 `### 标题` + 简介
- API 层保留原始 Markdown artifact，UI 解析失败时显示空结果或错误

创建项目本身不是概念接口干的，而是前端选中概念后再调用项目创建 action。因此 Concept Gacha 的后端职责只到“生成概念”，真正持久化仍复用普通项目创建链路。

## 数据模型

Concept Gacha 没有独立表。它的产物是一个普通 `Project`：

- `name` <- 选中概念的标题
- `description` <- 选中概念的简介
- `length_preset` <- 用户在概念页选择的篇幅范围
- `style_profile_id` / `plot_profile_id` <- 用户在概念页预先挂载的档案
- `default_provider_id` / `default_model` <- 用户在概念页选定的调用配置

用户原始灵感不会在概念生成阶段单独落表；概念卡本身也是一次性中间结果，不会以独立资产保存到数据库里。

## Prompt / LLM 调用要点

概念抽卡的 Prompt 设计集中在 `api/app/prompts/concept.py`：

- 3 张卡共享同一故事主轴，不能写成 3 本完全不同的小说
- 差异化来自不同卖点切口，而不是固定平台流派标签
- 一张优先突出主角身份与开局处境
- 一张优先突出机制、系统或核心玩法
- 一张优先突出人物关系、对抗局面或情绪钩子

新版 Prompt 不再把 3 张卡硬编码为“番茄流 / 起点流 / 反差萌流”，而是要求模型先理解灵感的共同主轴，再从不同入口包装成可选方向。

新版 Prompt 还增加了几条明确约束：

- 简介按题材决定是否使用标签式开头
- 文风更接近成熟网文简介，而不是广告投流文案
- 示例用于学习节奏与包装方式，不允许照搬示例设定
- 标题和简介都要保持网文味，但优先自然，不要生硬

用户消息非常简单，只传灵感和目标数量，由 `build_concept_generate_user_message()` 负责。差异化主要靠 system prompt 完成。

## 关键文件索引

- `web/app/(workspace)/projects/new/page.tsx`
- `web/components/concept-gacha-page.tsx`
- `web/lib/length-presets.ts`
- `web/lib/api-client.ts`
- `api/app/api/routes/novel_workflows.py`
- `api/app/services/novel_workflow_pipeline.py`
- `api/app/services/novel_workflow_agents.py`
- `api/app/prompts/concept.py`
- `api/app/services/projects.py`

## 相关章节

- [20 项目](./20-projects.md) — 抽卡确认后进入普通项目生命周期
- [15 LLM Provider 接入](../10-architecture/15-llm-provider-integration.md) — 为什么必须先选可用 Provider
- [30 Prompt 语料总览](../30-prompt-engineering/30-prompt-overview.md) — `prompts/` 语料与生产 Prompt 的关系
