# Persona

完整开发者文档见 [wiki/](./wiki/README.md)。

Persona 是一个单用户、BYOK、约束式的 AI 长篇创作平台。

## 目录

- `api/`: FastAPI + SQLAlchemy + Alembic + LangChain adapter
- `web/`: Next.js App Router + TanStack Query + React Hook Form + Zod
- `docker-compose.yml`: 本地 Postgres

## 快速开始

### 一键启动（推荐）

```bash
cd Persona
make dev
```

说明：
- 会先检查 Postgres 容器，已运行则跳过启动
- 会检查 `8000/3000` 端口，后端或前端已运行则跳过启动
- 首次会自动执行依赖安装（`uv sync`、`pnpm install`）
- 使用 `make status` 查看状态，`make stop` 停止 8000/3000 端口上的前后端服务

### 1. 启动数据库

```bash
cd Persona
docker compose up -d
```

### 2. 启动后端

```bash
cd Persona/api
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd Persona/web
cp .env.local.example .env.local
pnpm install
pnpm dev
```

打开 `http://localhost:3000`。

## 验证

```bash
cd Persona/api && uv run pytest -q
cd Persona/web && pnpm test
cd Persona/web && pnpm build
```

## GitHub Wiki Sync

仓库内的 `wiki/` 目录是文档事实源。GitHub 单独 Wiki 通过 [sync-github-wiki.yml](/Users/zhouzirui/code/test/AI-NOVEL/Persona/.github/workflows/sync-github-wiki.yml) 自动同步。

要让自动同步生效，需要在 GitHub Actions secrets 里配置：

- `WIKI_PUSH_TOKEN`

要求：

- 使用可访问 `nsxzhou/Persona.wiki.git` 的 Personal Access Token
- 令牌至少需要对该 Wiki 仓库有写权限
- 每次 `main` 分支上有 `wiki/**` 变更时，Action 会把 `wiki/README.md` 同步为 GitHub Wiki 的 `Home.md`
