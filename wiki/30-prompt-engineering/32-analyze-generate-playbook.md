# 32 ANALYZE-GENERATE 手法论

## 要解决什么问题

Style Lab 的终点不是“得到一份很长的分析报告”，而是把样本文风蒸馏成后续写作可直接执行的资产。`ANALYZE-GENERATE.md` 的核心价值就在于这条链路，本章把它重组为更贴近当前代码实现的四步法。

## 分析 -> Voice Profile -> 执行

### 第一步：输入判定，而不是立刻分析

在真正发 Prompt 之前，Worker 会先做文本识别，见 `api/app/services/style_analysis_text.py:119`：

- 文本类型：章节正文 / 口语字幕 / 混合文本
- 是否有时间戳
- 是否有说话人标签
- 是否有噪声标记
- 是否需要批处理

这一步的重要性在于：后续 Prompt 的证据定位方式和措辞强依赖它。

### 第二步：先做“证据驱动分析”，不要急着生成风格模仿 Prompt

分块分析与聚合 Prompt 的目标不是“写出一个像样的摘要”，而是尽量把文风证据按固定维度摊开，见：

- `build_chunk_analysis_prompt()`：`api/app/prompts/style_analysis.py`
- `build_merge_prompt()`：`api/app/prompts/style_analysis.py`
- `REPORT_TEMPLATE`：`api/app/prompts/style_analysis.py`

这一步的产物应该回答：

- 高频表达是什么
- 句式和节奏长什么样
- 标点、意象、场景策略是什么
- 哪些只是弱判断，哪些已经证据充分

如果直接跳过分析去写生成 Prompt，最后往往只会得到一堆“文学气质、节奏感、画面感”这种无执行价值的抽象词。

### 第三步：把长报告压缩成 Voice Profile

完整报告适合审阅，但不适合每次生成都整份注入。于是有了 `build_style_profile_prompt()`，定义在 `api/app/prompts/style_analysis.py`。

Voice Profile 的目标不是复述报告，而是提炼可直接进入后续写作系统提示词的可执行资产。它要求：

- 结构紧凑
- 禁令明确
- 可直接拼入系统提示词
- 去样本化（样本中的人物名、专属设定词改写为可跨作品复用的原型）

这一步相当于把“分析报告”压成“写作约束卡”。

## 为什么要分三步，而不是一步到位

### 1. 长样本与短生成是两种任务

- 分析任务要求“证据充足、分类清晰、尽量穷尽”
- 生成任务要求“高密度、低歧义、可复用”

一个 Prompt 同时追求这两者，通常会两头都做差。

### 2. 报告可读性与执行稳定性不是同一个目标

报告面向人类审阅，允许更细、更长、更解释性。

Voice Profile 面向后续模型执行，要求：

- 结构紧凑
- 禁令明确
- 可直接拼入系统提示词

### 3. 允许作者在中间层手工修正

Style Lab 把 Voice Profile 设计成可编辑层，前端保存链路见 `web/components/style-lab-profile-view.tsx:17` 与 `web/hooks/use-style-lab-wizard-logic.ts:281`。

这意味着作者不必接受模型原样产物：

- 报告可以只读保留作证据账本
- Voice Profile 可以人工去噪、继续人工修辞或删改硬约束

## 与当前代码实现的对应关系

| 手法论阶段 | 当前代码 |
| --- | --- |
| 输入判定 | `style_analysis_text.py` |
| 分块分析 | `StyleAnalysisPipeline._analyze_chunk()` |
| 全局聚合 | `StyleAnalysisPipeline._merge_chunks()` |
| 完整报告 | `StyleAnalysisPipeline._build_report()` |
| Voice Profile | `StyleAnalysisPipeline._build_profile()` |
| 保存档案 | `StyleProfileService.create()` |

## 常见坑 / 调试指南

| 症状 | 常见原因 | 处理思路 |
| --- | --- | --- |
| 摘要看着对，但写出来还是有 AI 味 | 摘要太抽象，没有落到句式/词汇/禁令 | 回到报告层补更具体证据 |
| Voice Profile 太长太散 | 把报告原样压进去了，没有做第二次抽象 | 重写 Voice Profile |
| 报告很长但没法复用 | 没有把“结论”和“证据账本”分层 | 保留报告只读，把操作性内容收进 Voice Profile |

## 相关章节

- [26 Style Lab](../20-domains/26-style-lab.md) — 这条手法论在产品里的外观
- [27 Style Analysis 管道](../20-domains/27-style-analysis-pipeline.md) — 后台具体怎么跑
- [31 Prompt ↔ Schema 强绑定](./31-prompt-schema-coupling.md) — 为什么模板与契约必须同步
