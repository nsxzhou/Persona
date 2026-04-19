# 15 LLM Provider 接入（BYOK）

## 要解决什么问题

Persona 的所有 AI 能力都建立在 BYOK（Bring Your Own Key）之上。Provider 层要解决的不是“多厂商 SDK 拼装”，而是：

- 用一套 OpenAI-compatible 契约接入不同网关
- 安全保存用户 API Key，并避免前端回显明文
- 给项目、Style Lab 与编辑器提供统一的模型调用入口
- 在连接失败、Provider 被禁用或正在被引用时，给出明确的业务错误

## 关键概念与约束

### 只支持 OpenAI-compatible，不做厂商特化

核心调用集中在 `api/app/services/llm_provider.py:18` 的 `LLMProviderService`：

- `_build_model()` 用 `init_chat_model()` 构造 LangChain chat model，见 `api/app/services/llm_provider.py:19`
- `test_connection()` 用一条最小 `Reply with OK` 请求做连通性探针，见 `api/app/services/llm_provider.py:44`
- `stream_messages()` / `invoke_completion()` 为上层业务统一提供流式与非流式入口，见 `api/app/services/llm_provider.py:72` 与 `api/app/services/llm_provider.py:82`

这条设计的意义是：Persona 不关心“你接的是 OpenAI、OpenRouter、LiteLLM、Azure OpenAI 还是别的代理”，只关心它是否暴露出一条稳定的 OpenAI-compatible chat completions 接口。

### Provider 的生命周期是 CRUD + test + 引用保护

HTTP 入口都在 `api/app/api/routes/provider_configs.py`：

- `GET /api/v1/provider-configs` 列出现有配置，见 `api/app/api/routes/provider_configs.py:22`
- `POST /api/v1/provider-configs` 新建配置，见 `api/app/api/routes/provider_configs.py:31`
- `PATCH /api/v1/provider-configs/{provider_id}` 编辑配置，见 `api/app/api/routes/provider_configs.py:45`
- `POST /api/v1/provider-configs/{provider_id}/test` 执行连通性测试，见 `api/app/api/routes/provider_configs.py:61`
- `DELETE /api/v1/provider-configs/{provider_id}` 删除配置，见 `api/app/api/routes/provider_configs.py:75`

业务规则在 `api/app/services/provider_configs.py`：

- `create()` / `update()` 负责加密存储与字段归一化，入口在 `api/app/services/provider_configs.py:51` 与 `api/app/services/provider_configs.py:82`
- `test_connection_and_update()` 既测连通性，也回写最近测试状态，入口在 `api/app/services/provider_configs.py:120`
- `delete()` 会拒绝删除仍被项目或 Style Lab 资产引用的 Provider，入口在 `api/app/services/provider_configs.py:156`
- `ensure_enabled()` 是项目创建、概念抽卡、Style Lab 建任务前的最后一道保护，入口在 `api/app/services/provider_configs.py:173`

### API Key 永远只明文出现一次

敏感信息处理由 `api/app/core/security.py:33` 与 `api/app/services/provider_configs.py:63` 负责：

- 入库前先 `encrypt_secret()`
- 同时单独保存 `api_key_hint_last4`
- 前端 API 只拿到掩码，不拿到密钥正文

对应的前端文案也明确承认这一点：

- `web/components/provider-config-form-dialog.tsx:44` 说明“前端不会回显明文”
- `web/components/provider-configs-page-view.tsx:177` 只展示 `api_key_hint`

### 超时、重试与脱敏来自全局 Settings

Provider 本身不携带独立超时字段；模型调用时统一读取全局配置：

- `Settings.llm_timeout_seconds` 定义在 `api/app/core/config.py:49`
- `Settings.llm_max_retries` 定义在 `api/app/core/config.py:54`
- `_build_model()` 把这两个值喂给 LangChain，见 `api/app/services/llm_provider.py:32`

测试失败时，错误摘要还会经过脱敏：

- `ProviderConfigService.test_connection_and_update()` 调用 `redact_sensitive_text()` 压缩并清洗错误消息，见 `api/app/services/provider_configs.py:138`

这意味着 Persona 的重试/超时策略是“全局统一”，不是“每个 Provider 自带一套调参面板”。

### 前端配置页是 React Query + RHF/Zod 的薄壳

页面入口在 `web/app/(workspace)/settings/models/page.tsx:1`，主要组件链路是：

- `web/components/provider-configs-page-view.tsx:15` 负责 list / test / delete / 打开表单
- `web/components/provider-config-form-dialog.tsx:18` 负责 create/edit 弹窗
- `web/components/provider-form-fields.tsx:16` 负责字段复用
- `web/lib/validations/provider.ts:12` 统一定义 Zod schema 与默认值

从交互上看，这一页只暴露四个最关键字段：

- `label`
- `base_url`
- `api_key`
- `default_model`

外加一个 `is_enabled` 开关。Persona 明确不做“自动探测模型列表”“自动计费”“多供应商特性面板”。

## 实现位置与扩展点

### 关键文件

| 文件 | 用途 |
| --- | --- |
| `api/app/api/routes/provider_configs.py` | Provider CRUD / test / delete 的 HTTP 入口 |
| `api/app/services/provider_configs.py` | Provider 业务规则、加密、引用保护 |
| `api/app/services/llm_provider.py` | 统一模型构造、流式/非流式调用 |
| `api/app/core/security.py` | API Key 的 AES-GCM 加解密 |
| `api/app/core/config.py` | 超时、重试、加密密钥、Cookie 等全局配置 |
| `web/app/(workspace)/settings/models/page.tsx` | 模型配置页入口 |
| `web/components/provider-configs-page-view.tsx` | 列表与操作按钮 |
| `web/components/provider-config-form-dialog.tsx` | 新增 / 编辑弹窗 |
| `web/components/provider-form-fields.tsx` | 表单字段复用 |
| `web/lib/validations/provider.ts` | Zod 校验与默认值 |

### 扩展点

- 如果未来要支持“按 Provider 自定义 header / organization / extra params”，最自然的位置是扩展 `ProviderConfig` 模型与 `_build_model()`
- 如果未来要增加模型能力探测，应放在 Provider service 层，不要让前端直接探厂商 API
- 如果未来要支持非 OpenAI-compatible 原生 SDK，也应先在 `LLMProviderService` 包一层适配，而不是把厂商分支散到编辑器和 Style Lab

## 常见坑 / 调试指南

| 症状 | 常见原因 | 先看哪里 |
| --- | --- | --- |
| “测试连接”失败但项目仍能保存 | 新建项目只校验 Provider 已启用，不强制最近测试成功 | `api/app/services/projects.py:62` |
| 删除 Provider 报冲突 | 仍有未归档项目或 Style Lab 任务 / 档案引用它 | `api/app/services/provider_configs.py:163` |
| 前端改了配置却看不到原 API Key | 这是设计目标，不是 bug | `web/components/provider-config-form-dialog.tsx:44` |
| 同一个 Provider 在 Style Lab 能用，在项目里报“未启用” | `is_enabled` 被关掉了，`ensure_enabled()` 拦截 | `api/app/services/provider_configs.py:173` |
| 模型调用超时 | 超时来自 `Settings.llm_timeout_seconds`，不是单个 Provider 字段 | `api/app/core/config.py:49` |

## 相关章节

- [10 整体架构总图](./10-high-level-architecture.md) — Provider 在系统中的位置
- [12 前端架构](./12-frontend-architecture.md) — Server/Client 两套 API 调用面如何共用契约
- [13 数据模型](./13-data-model.md) — `provider_configs` 表结构与引用关系
- [14 鉴权与 Session](./14-auth-and-session.md) — setup 会同时创建首个 Provider
- [22 Zen Editor](../20-domains/22-zen-editor.md) — 编辑器如何消费默认 Provider
- [26 Style Lab](../20-domains/26-style-lab.md) — 分析任务如何选择 Provider 与模型
- [42 配置与环境变量](../40-operations/42-configuration.md) — 超时、重试、密钥与 CORS 的环境变量
