# 31 Prompt ↔ Schema 强绑定规约

## 要解决什么问题

Persona 有两条容易出事故的链路：

- Editor Prompt 改了，但 API request/response schema 没改
- Style Lab 输出模板改了，但 RootModel / payload 解析没改

这不是抽象风险，而是本项目被 `AGENT.md` 明确上升为硬规则的问题。

## 关键概念与约束

### 权威规则先看 `AGENT.md`

根目录 `AGENT.md:40` 明确写道：

- Prompt 模板与 Pydantic 结构化输出 Schema 高度耦合
- 修改其中一方时，必须全局检索对应另一方并同步修改

同一份文档还给出两条补充约束：

- 状态对象必须是纯数据结构，见 `AGENT.md:42`
- Request / Response 必须使用 Pydantic V2 API，见 `AGENT.md:25`

因此本章不是在发明新规则，而是在解释项目里这条规则具体长什么样。

### 例子 1：Memory Sync 的 Request/Response 契约

Schema 定义在 `api/app/schemas/editor.py`：

- `BibleUpdateRequest`，见 `api/app/schemas/editor.py:30`
- `BibleUpdateResponse`，见 `api/app/schemas/editor.py:37`

对应 Prompt 构建在 `api/app/services/editor_prompts.py`：

- system prompt：`build_bible_update_system_prompt()`，见 `api/app/services/editor_prompts.py:542`
- user message：`build_bible_update_user_message()`，见 `api/app/services/editor_prompts.py:546`
- output 解析：`parse_bible_update_response()`，见 `api/app/services/editor_prompts.py:524`

这里的强绑定关系是：

- Schema 约定了只有 `proposed_runtime_state`、`proposed_runtime_threads`、`changed`
- Prompt 明确要求模型输出两个 `##` 区块
- 解析器假设第二个区块标题就是 `## 伏笔与线索追踪`

如果你把标题、字段名或返回语义改掉任何一个点，另外两个地方都必须一起改。

### 例子 2：Style Lab 的 Markdown RootModel 契约

Style Lab 的几个输出类型被封装成 RootModel：

- `AnalysisReportMarkdown`，见 `api/app/schemas/style_analysis_jobs.py:27`
- `StyleSummaryMarkdown`，见 `api/app/schemas/style_analysis_jobs.py:34`
- `PromptPackMarkdown`，见 `api/app/schemas/style_analysis_jobs.py:41`

它们对应的 Prompt 模板在 `api/app/services/style_analysis_prompts.py`：

- `REPORT_TEMPLATE`，见 `api/app/services/style_analysis_prompts.py:22`
- `STYLE_SUMMARY_TEMPLATE`，见 `api/app/services/style_analysis_prompts.py:52`
- `PROMPT_PACK_TEMPLATE`，见 `api/app/services/style_analysis_prompts.py:85`

这说明 Persona 选择的是 **Markdown-First** 契约，而不是 JSON-first：

- Schema 只要求“这是一个非空 Markdown 字符串”
- Prompt 通过标题层级、章节顺序和固定模板来约束结构
- 下游持久化字段也是 `Text`，不要求逐字段反序列化

好处是跨模型兼容性强；代价是改标题层级或章节顺序时，要同步修正文档、解析预期和测试。

### 例子 3：前端表单校验也是契约的一部分

并不是只有后端 Pydantic 才算 Schema。前端 Zod 表单同样是 Prompt/资产流转的一环：

- Provider 表单校验：`web/lib/validations/provider.ts:12`
- Style Lab 保存表单校验：`web/lib/validations/style-lab.ts:3`

例如 Style Lab 保存档案时，前端要求：

- `styleName` 非空
- `styleSummaryMarkdown` 非空
- `promptPackMarkdown` 非空

这与后端 `StyleProfileCreate` / `StyleProfileUpdate` 的字段约束是一致的，见 `api/app/schemas/style_profiles.py:8` 与 `16`。

## 实现位置与扩展点

### 一条实用检查清单

当你修改 Prompt 时，至少要反查这四层：

1. 对应的 Pydantic Schema 或 RootModel
2. 对应的解析函数或 assembler
3. 对应的前端 TS 类型 / Zod 表单
4. 对应的测试或 OpenAPI 产物

典型组合如下：

| Prompt 文件 | 对应契约 |
| --- | --- |
| `api/app/services/editor_prompts.py` | `api/app/schemas/editor.py`、`web/lib/api/generated/openapi.ts` |
| `api/app/services/style_analysis_prompts.py` | `api/app/schemas/style_analysis_jobs.py` |
| `api/app/services/editor_prompts.py` 中档案保存相关 Prompt | `api/app/schemas/style_profiles.py`、`web/lib/validations/style-lab.ts` |

### 修改时最容易漏掉的地方

- 只改 Prompt 文案，忘了改 parser
- 只改后端 Schema，忘了更新前端生成类型
- 只改 RootModel 描述，忘了测试里仍在断言旧标题

## 常见坑 / 调试指南

| 症状 | 常见原因 | 先看哪里 |
| --- | --- | --- |
| 模型输出看起来“差不多”，但接口 500 | parser 仍按旧标题/旧字段切分 | `editor_prompts.py` / `style_analysis_prompts.py` |
| 前端表单能保存，后端却 422 | Zod 与 Pydantic 约束不一致 | `web/lib/validations/*` 与 `api/app/schemas/*` |
| OpenAPI 类型和后端实际不一致 | 后端改了没重新 codegen | `web/package.json:9` |

## 相关章节

- [22 Zen Editor](../20-domains/22-zen-editor.md) — Editor Prompt 的主要消费者
- [26 Style Lab](../20-domains/26-style-lab.md) — 风格档案保存链路
- [27 Style Analysis 管道](../20-domains/27-style-analysis-pipeline.md) — Markdown-First 分析产物
- 根目录 `AGENT.md` — 本章所解释规则的权威来源
