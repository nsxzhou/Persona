# AI 编码助手行为与规范指南 (AGENT.md)

本文档是该项目的最高级编码约束。**任何 AI 助手在开始处理任务前，必须严格遵守本指南中的规则。**

## 1. AI 行为与工作流约束 (Agent Directives)

- **包管理器约束**：
  - **后端（`api/` 目录）**：强制在 `api/` 目录下使用 `uv` 进行依赖管理。禁止使用 `pip` 或直接修改 `requirements.txt`，必须维护 `api/uv.lock`。
  - **前端（`web/` 目录）**：强制在 `web/` 目录下使用 `pnpm`。禁止使用 `npm` 或 `yarn`，必须维护 `web/pnpm-lock.yaml`。
- **先阅读，后修改**：在进行任何代码修改前，必须先使用检索工具理解当前的架构。**对于业务逻辑的修改，必须同步检索并阅读对应的 Pydantic Schema/TypeScript Interface 及现有的单元测试文件，确保不破坏现有契约。**
- **避免猜测**：遇到不确定的类型或函数签名，必须去溯源查找。严禁凭空伪造 API 或假设字段存在；找不到定义时应主动扩大搜索范围（如使用 Grep）。
- **最小化变更**：只修改为完成任务所必需的代码。不要随意重构与当前任务无关的逻辑，不要擅自更改核心配置。
- **保持一致性**：新代码的命名风格、注释习惯、错误处理方式必须与周围代码保持一致。

## 2. 后端开发规范 (Backend: FastAPI + SQLAlchemy)

**技术栈**: Python 3.11+, FastAPI, SQLAlchemy 2.0 (Async), Pydantic V2, Alembic

### 2.1 架构分层
严格区分职责，禁止在 Router 中直接编写复杂的业务逻辑或数据库查询：
- **Router (`api/app/api/routes/`)**: 仅负责接收请求、解析参数（依赖注入）、调用 Service 层，以及格式化返回值。
- **Service (`api/app/services/`)**: 包含核心业务逻辑，协调多个数据模型或外部服务。
- **Repository (`api/app/db/repositories/`)**: 仅负责与数据库的直接交互（CRUD），隐藏 SQLAlchemy 查询细节。

### 2.2 类型与校验 (Typing & Validation)
- **现代 Python 语法**：强制使用 Python 3.11+ 类型提示（如 `list[str]`, `dict[str, Any]`, `str | None`）。所有函数必须有明确的参数和返回类型。
- **依赖注入最佳实践**：FastAPI 的依赖注入强制使用 `Annotated`（如 `session: Annotated[AsyncSession, Depends(get_db_session)]`），提升代码可读性与类型推导。
- **Pydantic V2 规范**：Request 和 Response 必须使用 Pydantic Schema。强制使用 V2 API（如 `model_validate`, `model_dump`），禁止使用 V1 遗留方法（`parse_obj`, `dict`）。使用 `Field` 进行严格的边界与默认值校验。

### 2.3 数据库操作规范 (Database Operations)
- **纯异步与 2.0 语法**：统一使用 `asyncpg` 和 SQLAlchemy 2.0。强制使用 2.0 风格的构建器（`select()`, `insert().returning()`），禁止使用遗留的 `session.query()`。
- **事务管理 (Transaction Management)**：
  - **常规请求**：推荐由 FastAPI 依赖（`get_db_session`）统一接管 `commit()` 和 `rollback()`。
  - **复杂业务与后台任务**：在需要精细控制或后台任务中，必须使用异步上下文管理器（`async with session.begin():`）实现工作单元（Unit of Work）模式，确保事务的原子性与隔离。
- **性能防范 (N+1)**：
  - 处理关联数据时，一对多/多对多必须使用 `selectinload`，多对一/一对一使用 `joinedload`。
  - 推荐在核心查询链路上使用 `raiseload('*')` 严格阻断意外的延迟加载（Lazy Loading）引发的 N+1 问题。

### 2.4 大模型管道与状态机 (LLM Module & State Machine Directives)
- **Prompt 与 Schema 强绑定**：大模型的 Prompt 模板与 Pydantic 结构化输出 Schema 高度耦合。修改其中一方时，**必须全局检索对应的另一方并同步修改**。务必确保 Prompt 中对输出格式的描述（包含字段名、类型、是否可选）与 Pydantic 字段完全对齐，防止反序列化失败。
- **复用模型实例**：禁止在分块处理循环或图节点（Node）中频繁实例化 LLM 客户端，必须在 Pipeline/Graph 初始化阶段完成构建并全局注入复用，避免连接池与 CPU 性能损耗。
- **状态机流转约束（State Machine Rules）**：
  - 状态（State）对象必须是纯粹的数据结构，严禁在状态对象中挂载数据库 Session 或网络连接等不可序列化的对象。
  - 节点（Node）的业务逻辑必须是纯函数或只通过明确定义的返回值触发状态更新，严禁在节点内部隐式突变（Mutate）全局变量或其他节点的状态。

### 2.5 内存与大文件处理 (Memory Safety)
- **禁止一次性加载**：处理用户上传的文本或数据库的大量历史任务时，严禁使用 `.read()` 读取整个文件或 `result.all()` 提取全量数据。
- **强制流式/批量处理**：
  - **数据库**：使用 SQLAlchemy 2.0 的 `result.stream_scalars()` 或 `yield_per()` 按批次消费数据；批量更新必须使用 `update().where(...)` 或 `update().values(...)` 而非逐行修改。
  - **文件流处理**：大文件上传使用 FastAPI 的 `UploadFile.file.read(chunk_size)`，返回大数据集必须使用 `StreamingResponse`。
  - **并发流**：对于高度并发的任务，利用 Python 3.11+ 的 `asyncio.TaskGroup` 结合 `Semaphore` 进行安全的并发数控制。

### 2.6 错误处理机制 (Error Handling)
- 统一异常抛出机制：使用自定义的 HTTP Exception 抛出业务错误，并在全局 exception handler 中统一捕获并返回标准格式的 JSON 错误响应。
- 完善日志记录：关键的业务节点和异常捕获处必须使用标准化日志进行记录。

## 3. 前端开发规范 (Frontend: Next.js + React + Tailwind)

**技术栈**: Next.js (App Router), React 19, TypeScript, Tailwind CSS 4, shadcn/ui

### 3.1 RSC 边界划分与数据传递 (React Server Components)
- **默认 Server Components**：所有组件默认作为 RSC 运行，以优化性能和减少客户端 JS 体积。服务端敏感逻辑（如数据库操作）所在的文件必须引入 `server-only`，防止误泄露。
- **精准使用 `'use client'`**：只有当组件确实需要 React 状态 (`useState`, `useEffect`)、生命周期、或浏览器 API 时，才添加 `'use client'` 指令。
- **下放状态**：将 Client Components 尽量推向组件树的叶子节点，避免在顶层 Layout 或 Page 滥用 `'use client'`。
- **跨边界 Props 传递**：从 Server Component 向 Client Component 传递的 Props 必须是**可序列化的（Serializable）**（如纯数据对象）。严禁跨边界传递非 `'use server'` 标记的函数或复杂类实例。

### 3.2 状态、数据流与 React 19 新特性
- **服务端数据获取**：优先在 Server Components 中直接使用 `async/await` 获取数据。
- **React 19 表单与乐观更新**：处理表单提交时，强制优先使用 React 19 的原生 Hooks（如 `useActionState` 处理状态, `useFormStatus` 处理加载态, `useOptimistic` 处理乐观 UI），废弃 React 18 时代的冗余 `useState` 模式。
- **Server Actions 与 React Query 的深度协同**：
  - 简单的服务端数据修改直接调用 Server Actions。
  - 对于**需要复杂客户端状态反馈**（如手动缓存失效、重试、复杂的乐观更新）的操作，**必须将 Server Action 作为 `@tanstack/react-query` 的 `mutationFn` 传入**（即 `useMutation({ mutationFn: myServerAction })`）。
- **表单校验**：使用 `react-hook-form` 配合 `zod` 进行严格的表单状态管理，Server Actions 内部必须对传入的数据再次使用 Zod 进行二次校验。

### 3.3 样式与 UI 规范 (Tailwind CSS 4 & cn)
- **Tailwind 4 规范**：拥抱 Tailwind v4 的 CSS-first 架构（通过 `@theme` 定义变量）。避免在代码中硬编码魔法数值。
- **动态样式安全 (`cn` 工具)**：当需要动态拼接类名时，必须使用 `cn` 工具函数（`clsx` + `tailwind-merge`）以避免样式覆盖冲突。
- **复杂变体管理 (`cva`)**：严禁在 `cn()` 内部编写深层嵌套的三元表达式。对于具有多种视觉变体（Variants）的组件，必须使用 `class-variance-authority` (cva) 进行结构化定义。
- **组件复用**：基于 `shadcn/ui` 构建基础组件（位于 `components/ui/`），业务组件放置于 `components/`。禁止重复造轮子。

### 3.4 目录与文件组织 (Directory Structure)
- `app/`: 仅包含 Next.js 路由文件（`page.tsx`, `layout.tsx`, `route.ts` 等）。
- `components/`: 存放所有可复用的 React 组件。
- `lib/`: 存放无副作用的工具函数、类型定义和 API 客户端代码。
- `hooks/`: 存放自定义 React Hooks。

## 4. 测试与质量保证 (Testing & Delivery)

- **无验证，不交付**：AI 在修改核心业务逻辑后，必须运行相关的 `pytest` 单元测试，并确保未引入退化。
- **后端测试规范**:
  - 强制配置 `pytest-asyncio` 的 `strict` 模式，避免混淆同步/异步测试。
  - 使用数据库的截断（Truncation）或事务回滚（Transaction Rollback）机制，确保每次测试间的数据隔离。
  - 接口集成测试必须通过 `TestClient` 或 `AsyncClient` 模拟真实的 HTTP 请求流转，并覆盖核心 Pydantic Validation 边界。
- **前端测试规范**:
  - 使用 `vitest` 和 React Testing Library 为核心 UI 组件和复杂业务逻辑编写单元测试。
  - **服务端/客户端渲染隔离验证**：在编写前端组件测试时，需注意模拟（Mock）Next.js 专属 API（如 `useRouter`），并验证组件在不同环境（Server/Client）下的纯函数表现。
  - 涉及复杂前端状态流转（如向导组件）的修改，应尽可能通过本地服务器启动并验证，确保没有引入不必要的全页重绘（Re-render）。
