# 40 本地开发与 Makefile

## 要解决什么问题

Persona 的开发体验依赖“一键把数据库、API、Worker、Web 都拉起来”。这章说明最少命令集、启动顺序和日志位置，帮助新贡献者快速进入可调试状态。

## 关键概念与约束

### `make dev` 是默认入口

`Makefile:15` 把本地开发环境拆成 `db -> api -> worker -> web -> status` 五段：

- `db`：确保 Postgres 容器已启动
- `api`：复制 `.env`、跑 `uv sync`、执行 Alembic、启动 FastAPI
- `worker`：启动统一后台 Worker，进程内并发轮询 Style Lab 与 Plot Lab 两类任务
- `web`：复制 `.env.local`、跑 `pnpm install`、启动 Next.js
- `status`：回显三大进程状态

根 README 也把 `make dev` 列为推荐方式，见 `README.md:13`。

### 首次启动会自动补依赖与 env 文件

Makefile 中的两个“偷懒但实用”的设计：

- 如果 `api/.env` 不存在，就从 `api/.env.example` 复制，见 `Makefile:32`
- 如果 `web/.env.local` 不存在，就从 `web/.env.local.example` 复制，见 `Makefile:71`

同时：

- 后端每次启动前都会 `uv sync`
- 前端每次启动前都会 `pnpm install`

这不是最高效，但对单用户本地开发最稳。

### 日志都进 `.run/`

三条关键日志路径在 `Makefile:9-11`：

- `.run/api.log`
- `.run/worker.log`
- `.run/web.log`

调试优先级通常是：

1. 先看 `make status`
2. 再看对应日志
3. 最后才怀疑代码本身

## 实现位置与扩展点

### 常用命令

| 命令 | 作用 |
| --- | --- |
| `make dev` | 启动完整开发环境 |
| `make db` | 只拉起 Postgres |
| `make api` | 只启动后端 |
| `make worker` | 启动统一后台 Worker（Style + Plot） |
| `make web` | 只启动前端 |
| `make status` | 查看数据库/API/Worker/Web 状态 |
| `make stop` | 停止 API / Worker / Web |
| `make logs` | 打印日志路径 |

### 纯手动启动方式

如果不想走 Makefile，也可以按根 README 的三段手动启动：

- 后端：`README.md:33`
- 前端：`README.md:43`
- 验证命令：`README.md:54`

## 常见坑 / 调试指南

| 症状 | 常见原因 | 先看哪里 |
| --- | --- | --- |
| `make dev` 卡在 API 启动 | Alembic 没跑过、数据库地址不通、缺少加密密钥 | `.run/api.log`、`api/.env` |
| Web 启起来了但登录失败 | API 没真正监听 8000 或 Cookie/CORS 配错 | `.run/api.log` |
| Style Lab 任务一直 pending | 后台 Worker 没启动，或日志中已报错退出 | `.run/worker.log`、`make status` |
| Plot Lab 任务一直 pending | 后台 Worker 没启动，或 Plot 执行循环在日志中报错 | `.run/worker.log`，再看 `api/app/worker.py` 与 `plot_analysis_worker.py` |
| 修改依赖后行为异常 | 手动用了 `pip`/`npm` 绕过项目约束 | 根 `AGENT.md:7` |

## 相关章节

- [10 整体架构总图](../10-architecture/10-high-level-architecture.md) — 三进程协作全景
- [41 数据库与迁移](./41-database-and-migrations.md) — Alembic 和 Postgres 的细节
- [42 配置与环境变量](./42-configuration.md) — `.env` / `.env.local` 字段说明
- [51 测试策略](../50-standards/51-testing-strategy.md) — 本地验证命令
