# 41 数据库与 Alembic 迁移

## 要解决什么问题

Persona 的后端既要支持本地 Postgres，也要兼容 SQLite 兜底和测试环境。迁移层要保证：

- 开发环境能一条命令升级到最新 schema
- 测试环境能临时切换到 SQLite
- Alembic 能识别当前 ORM 元数据并正确运行异步迁移

## 关键概念与约束

### 开发默认是 Postgres 17

`docker-compose.yml:1` 只定义了一个服务：

- 镜像：`postgres:17`
- 端口：`5432:5432`
- 数据卷：`persona-postgres-data`
- 健康检查：`pg_isready`

这也是 `make db` 与 `make dev` 的默认数据库目标。

### Alembic 配置在 `env.py`，不是单独的异步 runner 脚本

迁移入口在 `api/alembic/env.py`：

- `target_metadata = Base.metadata`，见 `api/alembic/env.py:29`
- 在线迁移走 `run_async_migrations()`，见 `api/alembic/env.py:65`
- 如果 URL 是同步写法，会自动补成 `sqlite+aiosqlite:///` 或 `postgresql+asyncpg://`，见 `api/alembic/env.py:94`

这让同一套迁移脚本可以在：

- 本地 Postgres
- SQLite 开发兜底
- 测试时注入的临时数据库

之间切换，而不用额外维护多套迁移入口。

### Session 工厂与迁移目标库是同一套 URL 源

应用运行时的 DB 入口是 `api/app/db/session.py:14`：

- `create_engine(database_url)`
- `create_session_factory(engine)`
- `get_db_session()`

迁移层如果没有被显式覆盖，也会回到 `Settings.database_url`，见 `api/alembic/env.py:87`。这保证“应用连接的库”和“迁移要打到的库”默认是一致的。

### 迁移历史能读出产品演进

当前版本目录在 `api/alembic/versions/`，核心节点包括：

- `0001_initial.py`：初始表结构
- `0002_style_lab.py`：Style Lab 资产引入
- `0006_style_job_leases.py`：任务租约与后台执行状态
- `0009_user_scoped_resources.py`：`user_id` scope 收口
- `0010_markdown_style_lab_payloads.py`：Style Lab 改为 Markdown-first 载荷
- `0011_style_job_pause.py`：任务暂停能力
- `c1d2e3f4a5b6_project_chapters.py`：章节树表
- `d3e4f5a6b7c8_chapter_memory_sync_fields.py`：章节级记忆同步字段
- `e4f5a6b7c8d9_add_auto_sync_memory_to_projects.py`：项目级自动同步开关

看迁移顺序能快速理解产品是如何从“基础 CRUD”长成现在这套系统的。

## 实现位置与扩展点

### 常用命令

| 命令 | 作用 |
| --- | --- |
| `cd api && uv run alembic upgrade head` | 升级到最新版本 |
| `cd api && uv run alembic downgrade -1` | 回滚一个版本 |
| `cd api && uv run alembic current` | 查看当前版本 |
| `cd api && uv run alembic history` | 查看迁移历史 |

### 何时需要新迁移

只要改了以下任一项，就应考虑加 Alembic 版本文件：

- `api/app/db/models.py`
- 关系、索引、唯一约束
- 默认值或列可空性

而像“只改 Prompt 文案”“只改前端类型”“只改 Service 逻辑”则不需要迁移。

## 常见坑 / 调试指南

| 症状 | 常见原因 | 先看哪里 |
| --- | --- | --- |
| `relation does not exist` | 忘了跑 `alembic upgrade head` | `README.md:39` |
| SQLite 能跑，Postgres 报错 | 迁移脚本只在一种方言下验证过 | `api/alembic/env.py:94` |
| 新字段模型里有，库里没有 | 只改了 ORM，没出 migration | `api/alembic/versions/` |
| 测试临时库没吃到最新 schema | 覆盖了 `sqlalchemy.url` 但没触发迁移 | `api/alembic/env.py:82` |

## 相关章节

- [13 数据模型](../10-architecture/13-data-model.md) — 当前 schema 的业务含义
- [40 本地开发与 Makefile](./40-local-dev-and-make.md) — `make api` 如何自动执行迁移
- [42 配置与环境变量](./42-configuration.md) — `PERSONA_DATABASE_URL`
