# 30 Prompt 语料总览

## 要解决什么问题

仓库里同时存在两类资产（Voice Profile 和 Story Engine）：

- `prompts/` 下的 461 份 Markdown 语料：偏“创作素材库 / Voice Profile 和 Story Engine库”
- `api/app/prompts/concept.py`、`section_router.py`、`beat.py`、`prose_writer.py`、`memory_sync.py`、`style_analysis.py`、`plot_analysis.py` 等：偏“生产运行时 Prompt 模板”

本章的目标不是逐文件导读，而是帮你建立两个判断：

- 哪些 Prompt 属于可复用的创作素材库
- 哪些 Prompt 才是当前产品功能真正在线调用的生产 Prompt

## 关键概念与约束

### `prompts/` 是通用语料库，不是逐个在线调用的运行时目录

当前仓库中 `prompts/*.md` 实际数量是 **461** 份。这些文件以编号命名，例如：

- `prompts/1.md:1` `全能网文主编角色加载`
- `prompts/11.md:1` `百万字节奏规划`
- `prompts/13.md:1` `战斗场景生成`
- `prompts/101.md:1` `奇幻地理与气候生成`
- `prompts/146.md:1` `伏笔回收与反转设计检查表`
- `prompts/293.md:1` `写作：环境渲染-雨夜`

它们更像“可采样、可改编、可迁移”的创作语料库，而不是“前端点一下就直接对应一个 API 路由”的运行时模板。

### 真正在线运行的 Prompt 在代码里

当前产品主链路真正调用的是两组代码内模板：

- `api/app/prompts/concept.py` / `section_router.py` / `beat.py` / `prose_writer.py` / `memory_sync.py`：Zen Editor / 概念 / 大纲 / 节拍 / Memory Sync
- `api/app/prompts/style_analysis.py`：Style Lab 分析 / 聚合 / 报告 / Voice Profile
- `api/app/prompts/plot_analysis.py`：Plot Lab sketch / skeleton / 分析 / Story Engine

例如：

- 概念抽卡：`build_concept_generate_system_prompt()` / `build_concept_generate_user_message()`
- Bible 更新：`build_bible_update_system_prompt()` / `build_bible_update_user_message()`
- 节拍生成与逐拍展开：`build_beat_generate_system_prompt()` / `build_beat_expand_system_prompt()`
- Style Lab 分块分析 / 聚合 / 报告 / Voice Profile：`build_chunk_analysis_prompt()`、`build_merge_prompt()`、`build_report_prompt()`、`build_voice_profile_prompt()`
- Plot Lab sketch / skeleton / 报告 / Story Engine：`build_sketch_prompt()`、`build_skeleton_reduce_prompt()`、`build_report_prompt()`、`build_story_engine_prompt()`

所以做开发时要先分清：

- 想理解“产品当前怎么跑” -> 先看 `api/app/services/novel_workflow_pipeline.py`、`api/app/services/novel_workflow_agents.py` 以及 `api/app/prompts/` 下的专职模块
- 想理解“项目积累了哪些通用写作资产” -> 再看 `prompts/`
- 运行时直接 import `api/app/prompts/*`，不再保留 `app.services.*_prompts` 兼容导出层

## 采样索引

### 1. 概念启动 / 项目起盘

这类 Prompt 适合项目刚立项时做方向探索：

- `prompts/1.md:1` `全能网文主编角色加载`
- `prompts/12.md:1` `黄金三章细纲`
- `prompts/122.md:1` `角色弧光 (Character Arc) 设计`

它们和线上 Concept Gacha 的关系是“理念相近、实现分离”。线上概念抽卡真正走的是 `api/app/prompts/concept.py` 的差异化三卡策略。

### 2. 大纲规划 / 节奏控制

这类 Prompt 对应“先规划后写”的心智：

- `prompts/11.md:1` `百万字节奏规划`
- `prompts/30.md:1` `百万字分卷日更表`
- `prompts/100.md:1` `全书大结局收束检查表`
- `prompts/146.md:1` `伏笔回收与反转设计检查表`

线上实现里，与它们最近的生产 Prompt 是卷级结构和节拍相关函数：`build_volume_generate_system_prompt()`、`build_volume_chapters_system_prompt()`、`build_beat_generate_system_prompt()`。

### 3. 正文续写 / 场景润色 / 对话

这类 Prompt 更接近“执笔层”：

- `prompts/13.md:1` `战斗场景生成`
- `prompts/14.md:1` `对话优化 (潜台词注入)`
- `prompts/111.md:1` `"Show, Don't Tell" 改写练习`
- `prompts/113.md:1` `五感环境氛围扩写`
- `prompts/293.md:1` `写作：环境渲染-雨夜`

对应的线上生产 Prompt 是编辑器续写与节拍展开链路，见 [22 Zen Editor](../20-domains/22-zen-editor.md) 与 [24 大纲与节拍](../20-domains/24-outline-and-beats.md)。

### 4. 世界观 / 圣经 / 设定构建

这类 Prompt 偏蓝图层：

- `prompts/101.md:1` `奇幻地理与气候生成`
- `prompts/103.md:1` `架空语言与黑话生成器`
- `prompts/117.md:1` `远古神话/传说生成器`
- `prompts/137.md:1` `宗教/教派教义生成`

线上生产 Prompt 则由 `api/app/prompts/section_router.py` 路由到 `world_building.py` / `characters.py` / `outline.py` / `chapter_plan.py` 等专职模块。

### 5. 风格 / 修辞 / 语感校准

这类 Prompt 更像“文字调音台”：

- `prompts/2.md:1` `文风与禁区锁`
- `prompts/112.md:1` `创意比喻与修辞生成器`
- `prompts/151.md:1` `意识流/心理独白写法`

线上 Style Lab 的产物并不直接来自这些编号 Prompt，而是来自一套更严格的 Markdown-First 分析与摘要模板；Plot Lab 也是同理，只是额外多了 skeleton 这一层。

### 6. 通用灵感工具 / 脑洞资产

这类 Prompt 覆盖题材、系统、职业、工具、营销玩法等长尾场景：

- `prompts/149.md:1` `战斗力崩坏补救方案`
- `prompts/209.md:1` `抽卡系统保底与概率设计`
- `prompts/280.md:1` `写作工具：随机事件生成器 (卡文救星)`

这也是为什么不适合对 `prompts/` 做逐文件 wiki 展开：它更像素材库，不像单一产品模块。

## 实现位置与扩展点

### 当前生产 Prompt 的三条主线

| 目录 / 文件 | 角色 |
| --- | --- |
| `prompts/*.md` | 通用创作 Prompt 语料库 |
| `api/app/prompts/concept.py`、`section_router.py`、`beat.py`、`prose_writer.py`、`memory_sync.py` | Novel Workflow 的概念 / 大纲 / 节拍 / 正文 / Memory Sync 生产 Prompt |
| `api/app/prompts/style_analysis.py` | Style Lab 分析、聚合、Voice Profile 生产 Prompt |
| `api/app/prompts/plot_analysis.py` | Plot Lab sketch、骨架、聚合、Story Engine 生产 Prompt |
| `api/app/schemas/novel_workflows.py` | Novel Workflow 请求 / 响应 / 状态 / 决策契约 |
| `api/app/schemas/style_analysis_jobs.py` | Style Lab 产物 RootModel 与状态常量 |
| `api/app/schemas/plot_analysis_jobs.py` | Plot Lab 产物 RootModel、skeleton schema 与阶段常量 |

### 扩展建议

- 新增线上功能 Prompt 时，优先加到 `api/app/prompts/` 下对应模块
- 只有当 Voice Profile 和 Story Engine不直接绑定某个在线接口、而是想沉淀成素材库时，才考虑放进 `prompts/`
- 修改线上 Prompt 时，一定同步检查对应 Schema 和测试，不要只改文案

## 常见坑 / 调试指南

| 症状 | 常见原因 | 先看哪里 |
| --- | --- | --- |
| 以为 `prompts/` 就是线上逻辑 | 混淆了语料库与生产模板 | `api/app/prompts/` 下的专职模块与 `api/app/services/novel_workflow_agents.py` |
| 新增 Prompt 文件后前端没任何变化 | `prompts/` 目录没有自动注册机制 | 路由和 Service 是否实际引用 |
| 风格分析输出结构不稳 | 只看 `prompts/`，没看 `STYLE_ANALYSIS_REPORT_SECTIONS` 和模板 | `api/app/schemas/style_analysis_jobs.py:11` |

## 相关章节

- [24 大纲与节拍](../20-domains/24-outline-and-beats.md) — 线上规划 Prompt
- [26 Style Lab](../20-domains/26-style-lab.md) — 线上风格分析 Prompt
- [31 Prompt ↔ Schema 强绑定](./31-prompt-schema-coupling.md) — 改 Prompt 时为什么要同步改 Schema
- [32 ANALYZE-GENERATE 手法论](./32-analyze-generate-playbook.md) — Style Lab 输出如何变成可执行资产
