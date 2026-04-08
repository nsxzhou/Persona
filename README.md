# Persona

Persona 是一个前后端分离的单用户 AI 创作基础平台。

## 目录

- `api/`: FastAPI + SQLAlchemy + Alembic + LangChain adapter
- `web/`: Next.js App Router + TanStack Query + React Hook Form + Zod
- `docker-compose.yml`: 本地 Postgres

## 快速开始

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

