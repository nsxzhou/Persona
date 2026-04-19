# 25 概念抽卡（Concept Gacha）

## 一句话定义 + 价值

Concept Gacha 是 Persona 的“新项目启动器”。它不是直接让用户填空创建项目，而是先让模型基于一段灵感生成 3 张差异化概念卡，再从中选一张落成真正的 Project。

## 用户视角流程

1. 用户进入 `/projects/new`。
2. 选择一个已启用的 Provider，可选填模型覆盖。
3. 输入灵感描述，点击“生成灵感卡”。
4. 页面展示 3 张概念卡，用户选择一张，并选定目标篇幅预设。
5. 确认后系统立刻创建项目，并跳转到项目详情页。

## 前端入口与组件链路

页面入口在 `web/app/(workspace)/projects/new/page.tsx:4`。它先通过 `getServerApi()` 拉取 Provider 列表，再把数据交给 `ConceptGachaPage`。

核心交互都在 `web/components/concept-gacha-page.tsx:28`：

- `handleGenerate()` 负责调用 `api.generateConcepts()`，见 `web/components/concept-gacha-page.tsx:42`
- `handleConfirm()` 负责把被选中的概念转换成真正的 `ProjectCreate` payload，见 `web/components/concept-gacha-page.tsx:65`
- `lengthPreset` 选择器让项目从一开始就带上篇幅目标，见 `web/components/concept-gacha-page.tsx:216`

这个页面有两个有意的产品选择：

- 概念卡固定一次给 3 张，鼓励用户在“方向差异”里做选择，而不是无限抽卡
- 创建项目时只写最少字段，其余 Bible 字段都留空，后续再逐步生成或人工完善

## 后端接口 / Service / Repository 链路

概念生成路由本身挂在 editor router 上，而不是 projects router 上：`api/app/api/routes/editor.py:37`。

Service 在 `api/app/services/editor.py:325`：

- 先通过 `ProviderConfigService.ensure_enabled()` 校验 Provider 可用
- 再拼装概念生成 system prompt 与 user message
- 最后用 `LLMProviderService.invoke_completion()` 做一次非流式调用

响应解析在 `api/app/services/editor_prompts.py:19`：

- 约定模型输出形如 `### 标题` + 简介
- 解析失败直接抛 `UnprocessableEntityError`

创建项目本身不是概念接口干的，而是前端选中概念后再调用项目创建 action。因此 Concept Gacha 的后端职责只到“生成概念”，真正持久化仍复用普通项目创建链路。

## 数据模型

Concept Gacha 没有独立表。它的产物是一个普通 `Project`：

- `name` <- 选中概念的标题
- `description` <- 选中概念的简介
- `inspiration` <- 用户原始灵感
- `length_preset` <- 用户在概念页选择的篇幅范围

也就是说，概念卡是一次性中间结果，不会以独立资产保存到数据库里。

## Prompt / LLM 调用要点

概念抽卡的 Prompt 设计集中在 `api/app/services/editor_prompts.py:693`：

- 概念 1 强调“番茄脑洞/情绪流”
- 概念 2 强调“起点世界/悬念流”
- 概念 3 强调“反差人设流”

这不是让模型自由发散，而是硬编码出“至少三种不同起步策略”，降低 3 张卡互相撞车的概率。

用户消息非常简单，只传灵感和目标数量，见 `api/app/services/editor_prompts.py:727`。差异化主要靠 system prompt 完成。

## 关键文件索引

- `web/app/(workspace)/projects/new/page.tsx`
- `web/components/concept-gacha-page.tsx`
- `web/lib/length-presets.ts`
- `web/lib/api-client.ts`
- `api/app/api/routes/editor.py`
- `api/app/services/editor.py`
- `api/app/services/editor_prompts.py`
- `api/app/services/projects.py`

## 相关章节

- [20 项目](./20-projects.md) — 抽卡确认后进入普通项目生命周期
- [15 LLM Provider 接入](../10-architecture/15-llm-provider-integration.md) — 为什么必须先选可用 Provider
- [30 Prompt 语料总览](../30-prompt-engineering/30-prompt-overview.md) — `prompts/` 语料与生产 Prompt 的关系
