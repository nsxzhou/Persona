# 42 配置与环境变量

## 要解决什么问题

Persona 的运行配置主要分成三类：

- 后端核心配置：数据库、加密、Session、LLM、Style Lab Worker
- 前端配置：API Base URL
- 安全相关配置：Cookie、脱敏、API Key 加密

本章按当前真实 `Settings` 和示例 env 文件展开，不讨论仓库里不存在的部署体系。

## 关键概念与约束

### 后端配置唯一入口是 `Settings`

所有后端环境变量最终都收口到 `api/app/core/config.py:16` 的 `Settings`：

- `database_url`：`PERSONA_DATABASE_URL`
- `encryption_key`：`PERSONA_ENCRYPTION_KEY`
- `session_cookie_name` / `session_cookie_secure` / `session_ttl_hours`
- `cors_allowed_origins`
- `llm_timeout_seconds` / `llm_max_retries`
- `storage_dir`
- `style_analysis_*` 一组 Worker 与管道参数

`get_settings()` 通过 `@lru_cache` 做单例缓存，见 `api/app/core/config.py:110`。

### `.env.example` 是最可信的字段清单

`api/.env.example` 覆盖了运行时最常用的变量：

- 数据库与加密：`api/.env.example:6`
- Session 与 CORS：`api/.env.example:16`
- LLM 超时与重试：`api/.env.example:31`
- Storage 与 Style Analysis：`api/.env.example:41`
- 真实 Provider 集成测试专用变量：`api/.env.example:65`

前端只有一个强依赖变量：`NEXT_PUBLIC_API_BASE_URL`，见 `web/.env.local.example:6`。

### 加密与脱敏是两件不同的事

敏感信息的处理分两层：

- **加密存储**：API Key 入库前做 AES-GCM，加密逻辑在 `api/app/core/security.py:33`
- **日志脱敏**：错误信息或 URL 被展示前先做文本清洗，逻辑在 `api/app/core/redaction.py:25`

这两层缺一不可：

- 只加密不脱敏，日志里仍可能泄露 token
- 只脱敏不加密，数据库泄露时仍是明文风险

### Style Lab 有自己的一组运行参数

`Settings` 里和 Style Lab 直接相关的变量包括：

- `PERSONA_STYLE_ANALYSIS_MAX_UPLOAD_BYTES`
- `PERSONA_STYLE_ANALYSIS_WORKER_ENABLED`
- `PERSONA_STYLE_ANALYSIS_POLL_INTERVAL_SECONDS`
- `PERSONA_STYLE_ANALYSIS_STALE_TIMEOUT_SECONDS`
- `PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY`
- `PERSONA_STYLE_ANALYSIS_MAX_ATTEMPTS`
- `PERSONA_STYLE_ANALYSIS_CHECKPOINT_URL`

它们分别影响：

- 上传体积上限
- Worker 是否启用
- 轮询频率
- 陈旧任务判定
- Chunk 并发数
- 重试次数
- Checkpointer 存储位置

## 实现位置与扩展点

### 常见配置组合

| 场景 | 关键配置 |
| --- | --- |
| 本地开发 | `PERSONA_SESSION_COOKIE_SECURE=false`、`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` |
| SQLite 兜底 | `PERSONA_DATABASE_URL=sqlite+aiosqlite:///./persona.db` |
| Worker 暂时关闭 | `PERSONA_STYLE_ANALYSIS_WORKER_ENABLED=false` |
| 独立 checkpoint 库 | 设置 `PERSONA_STYLE_ANALYSIS_CHECKPOINT_URL` |

### 新增配置项时的推荐落点

1. 先加到 `Settings`
2. 再补到 `.env.example` 或 `.env.local.example`
3. 如有必要，再补文档与运行时默认值说明

不要把“只有某个 Service 知道的魔法环境变量”散落在代码里。

## 常见坑 / 调试指南

| 症状 | 常见原因 | 先看哪里 |
| --- | --- | --- |
| 后端启动即报缺少加密密钥 | `PERSONA_ENCRYPTION_KEY` 未设置 | `api/app/core/config.py:101` |
| 登录接口成功，但浏览器不带 Cookie | `PERSONA_SESSION_COOKIE_SECURE=true` 且本地走 HTTP | `api/.env.example:16` |
| 本地 3000 调 8000 被浏览器拦 | CORS 白名单未包含前端地址 | `api/app/core/config.py:42` |
| Style Lab 任务一直卡住 | Worker 被禁用或轮询间隔过大 | `api/app/core/config.py:62` |
| Provider 报超时 | `PERSONA_LLM_TIMEOUT_SECONDS` 太小 | `api/app/core/config.py:49` |

## 相关章节

- [15 LLM Provider 接入](../10-architecture/15-llm-provider-integration.md) — 超时、重试、加密如何落到 Provider
- [16 SSE 与流式响应](../10-architecture/16-sse-and-streaming.md) — CORS 与 Cookie 会影响流式请求
- [40 本地开发与 Makefile](./40-local-dev-and-make.md) — env 文件如何被自动复制
- [41 数据库与迁移](./41-database-and-migrations.md) — `PERSONA_DATABASE_URL`
