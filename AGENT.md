# AI 编码助手行为与规范指南 (AGENT.md)

本文档是该项目的最高级编码约束。**任何 AI 助手在开始处理任务前，必须严格遵守本指南中的规则。**

## 1. AI 行为与工作流约束 (Agent Directives)

- **先阅读，后修改**：在进行任何代码修改前，必须先使用检索工具（如 SearchCodebase、Grep）或读取文件工具（Read）理解当前的架构、类型定义和现有模式。
- **避免猜测**：如果遇到不确定的类型或函数签名，必须去溯源查找，严禁凭空伪造 API 或假设字段存在。
- **最小化变更**：只修改为完成任务所必需的代码。不要随意重构与当前任务无关的逻辑，不要擅自更改 `package.json`、`pyproject.toml` 等核心配置。
- **保持一致性**：新代码的命名风格、注释习惯、错误处理方式必须与周围代码保持一致。

## 2. 后端开发规范 (Backend: FastAPI + SQLAlchemy)

**技术栈**: Python 3.11+, FastAPI, SQLAlchemy 2.0 (Async), Pydantic V2, Alembic

### 2.1 架构分层
严格区分职责，禁止在 Router 中直接编写复杂的业务逻辑或数据库查询：
- **Router (`api/routes/`)**: 仅负责接收请求、解析参数（依赖注入）、调用 Service 层，以及格式化返回值。
- **Service (`services/`)**: 包含核心业务逻辑，协调多个数据模型或外部服务。
- **Repository/DB (`db/`)**: 仅负责与数据库的直接交互（CRUD），隐藏 SQLAlchemy 的复杂查询细节。

### 2.2 类型与校验 (Typing & Validation)
- 强制使用 Python 类型提示（Type Hinting）。所有函数（包括内部函数）都必须有明确的参数类型和返回类型。
- 所有 API 的 Request 和 Response 必须使用 Pydantic Schema 进行定义和校验。

### 2.3 数据库操作规范 (Database Operations)
- **纯异步**：统一使用 `asyncpg` 和 SQLAlchemy 2.0 异步 Session (`AsyncSession`)。
- **性能防范**：严禁出现 N+1 查询。处理关联数据时，必须明确使用 `joinedload` 或 `selectinload` 进行预加载。

### 2.4 错误处理机制 (Error Handling)
- 统一异常抛出机制：使用自定义的 HTTP Exception 抛出业务错误，并在全局 exception handler 中统一捕获并返回标准格式的 JSON 错误响应。
- 完善日志记录：关键的业务节点和异常捕获处必须使用标准化日志进行记录。

## 3. 前端开发规范 (Frontend: Next.js + React + Tailwind)

**技术栈**: Next.js (App Router), React 19, TypeScript, Tailwind CSS 4, shadcn/ui

### 3.1 RSC 边界划分 (React Server Components)
- **默认 Server Components**：所有组件默认作为 RSC 运行，以优化性能和减少客户端 JS 体积。
- **精准使用 `'use client'`**：只有当组件确实需要 React 状态 (`useState`, `useEffect`)、生命周期、或浏览器 API 时，才添加 `'use client'` 指令。
- **下放状态**：将 Client Components 尽量推向组件树的叶子节点，避免在顶层 Layout 或 Page 滥用 `'use client'`。

### 3.2 状态与数据流 (State & Data Fetching)
- **服务端数据**：推荐使用 Next.js 的 Server Actions 进行数据变更（Mutations），使用 Server Components 直接获取数据。
- **客户端异步状态**：复杂的客户端异步请求必须使用 `@tanstack/react-query`，不建议使用原生 `useEffect` 抓取数据。
- **表单处理**：使用 `react-hook-form` 配合 `zod` 进行严格的表单状态管理和客户端/服务端双重校验。

### 3.3 样式与 UI 规范 (Styling & UI)
- **Tailwind 规范**：使用 Tailwind CSS 进行样式编写。当需要动态拼接类名时，必须使用 `cn` 工具函数（`clsx` + `tailwind-merge`）以避免样式冲突。
- **组件复用**：基于 `shadcn/ui` 构建基础组件（位于 `components/ui/`），业务组件放置于 `components/`。禁止重复造轮子。

### 3.4 目录与文件组织 (Directory Structure)
- `app/`: 仅包含 Next.js 路由文件（`page.tsx`, `layout.tsx`, `route.ts` 等）。
- `components/`: 存放所有可复用的 React 组件。
- `lib/`: 存放无副作用的工具函数、类型定义和 API 客户端代码。
- `hooks/`: 存放自定义 React Hooks。

## 4. 测试与质量保证 (Testing)

- **后端测试**: 必须使用 `pytest` + `pytest-asyncio` 进行接口集成测试，确保数据库状态隔离。
- **前端测试**: 使用 `vitest` 和 React Testing Library 为核心 UI 组件和复杂业务逻辑编写单元测试。