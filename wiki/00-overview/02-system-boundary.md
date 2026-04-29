# 02 系统边界与非目标

**不做什么**比**做什么**更能刻画一个系统。本章列出 Persona 的硬边界：什么在范围内、什么显式不做、模型 / 数据 / 账号层面各自有哪些假设。

---

## 一、身份与账号边界

### 单用户模型

- **一套部署只服务一个人**。数据库里只会有一个 `user` 记录
- 所有业务表（`projects`、`chapters`、`style_profiles`、`provider_configs`、`style_sample_files`、`style_analysis_jobs` 等）都有 `user_id` 外键并在每个 Service / Repository 操作中按 `user_id` 做 scope 隔离——但实际上只会匹配到那一个用户

**为什么保留 `user_id`**：如果未来确实要做多用户，现有的 scope 隔离逻辑不需要大改；同时这也让"资源归属"变成一个显式不可绕过的约束，避免测试时串库。

### 初始化：一次性 setup

- 首次启动数据库干净时，前端路由守卫会把用户重定向到 `/setup`
- `/setup` 页面完成三件事：创建唯一管理员账号、创建首个 Provider 配置、写入会话 Cookie
- 完成后 `user` 记录不可再创建——后端 `api/app/api/routes/setup.py` 会校验 DB 中已有用户时直接拒绝

### 不做的：注册 / 找回 / RBAC

- ❌ 公开注册入口——根本不存在
- ❌ 忘记密码 / 邮件验证——用户忘了密码只能直接改数据库
- ❌ RBAC / 角色 / 权限组——就一个人，没意义
- ❌ 多设备 session 管理 / 强制登出——HttpOnly Cookie 过期就完了
- ❌ 审计日志 / 登录历史——极客用户自己上 Postgres 看就行

### Session

- HttpOnly Cookie + 服务端 Session
- 访问 `/projects` / `/style-lab` / `/plot-lab` / `/settings/*` 等受保护页面时，工作区入口 `web/app/(workspace)/layout.tsx` 会先读取 setup 状态与当前用户；未初始化跳 `/setup`，未登录跳 `/login`
- setup / login 页的客户端提交逻辑由 `web/components/route-guards.tsx` 负责，成功后刷新 Query cache 并跳转到 `/projects`
- 后端每个受保护路由通过 `api/app/api/deps.py` 的 `CurrentUserDep` 依赖注入校验

详见 [14 鉴权、Session 与资源隔离](../10-architecture/14-auth-and-session.md)。

---

## 二、模型调用边界（BYOK）

### BYOK（Bring Your Own Key）

- Persona 本身**不代理** LLM 调用、**不做计费中转**
- 用户在 `/settings/models` 填写 **OpenAI-compatible** 接入点：`label`、`base_url`、`api_key`、`default_model` 与 `is_enabled`
- 数据库表 `provider_configs` 存储这些配置，`api_key` 字段使用对称加密入库，对外 API 返回掩码（只显示前 4 后 4 位）
- 真实调用时 `api/app/services/llm_provider.py` 读取 config，解密 api_key，通过 LangChain 的 `ChatOpenAI` 或等价包装器发起请求

### 统一 OpenAI-compatible

- **不按厂商拆原生协议**。不是每家厂商一套 SDK
- 官方 OpenAI、Anthropic（via OpenAI-compat proxy）、本地 LLaMA / Ollama、LiteLLM 代理、Azure OpenAI、豆包、Claude via Bedrock 等，只要暴露 OpenAI-compatible `/v1/chat/completions` 接口，都可通过"填 base_url + key"接入
- 简化了代码路径——只有一条 LangChain `ChatOpenAI` 使用方式
- 代价是**无法利用厂商特有的高级能力**（Claude 原生 tool use 格式、Anthropic native prompt caching 等）——这是有意的取舍

### 不做的：模型能力探测 / 自动定价

- ❌ 自动探测 Provider 支持哪些模型
- ❌ 自动计价 / token 消耗统计 / 用量分析——BYOK，用户去厂商看自己账单
- ❌ 模型降级 / 回退策略——用户手动切换 provider

### 超时与重试

- 超时与重试由 `api/app/core/config.py` 的 `Settings.llm_timeout_seconds` / `llm_max_retries` 统一决定
- Provider 配置本身没有独立的超时或重试面板
- Style / Plot 分析任务级别另有 lease、心跳和陈旧任务恢复机制

详见 [15 LLM Provider 接入](../10-architecture/15-llm-provider-integration.md)。

---

## 三、数据与存储边界

### Postgres 为主，SQLite 兜底

- 生产使用 **Postgres**，通过 `docker-compose.yml` 提供本地 dev 镜像
- 开发兜底 **SQLite**（常见本地路径是 `./persona.db`）——`Settings.database_url` 根据 `.env` 决定用哪个
- **Alembic 迁移同时兼容两边**——测试默认用 SQLite 跑

### 本地文件系统

- 配置项 `PERSONA_STORAGE_DIR`（默认 `./storage`）存放：
  - 原始 Style Lab 样本 TXT
  - Style Analysis 任务的增量日志与中间产物
  - Project 导出的 txt / epub（临时）
- 这些目录在 `.gitignore` 里，不入 git

### Checkpointer

- LangGraph 的 checkpointer 从 `database_url` 推导——Postgres 用 `PostgresSaver`，SQLite 用 `SqliteSaver`
- 可通过 `PERSONA_STYLE_ANALYSIS_CHECKPOINT_URL` 显式覆盖（例如把 checkpoint 放到独立 DB）

### 不做的：云存储 / CDN / 跨机同步

- ❌ 对象存储（S3 / 阿里 OSS）——用户自己想同步就 rsync
- ❌ 跨设备同步——单机单用户
- ❌ 备份策略——自己 `pg_dump`

详见 [13 数据模型](../10-architecture/13-data-model.md)、[41 数据库与迁移](../40-operations/41-database-and-migrations.md)。

---

## 四、功能边界

### ✅ 在范围内

- 项目 CRUD + 归档 / 恢复 + 挂载风格档案 + 导出 txt / epub
- 章节树（多级层次结构、排序、CRUD）
- Zen Editor（写作 + 自动保存 + 选区局部改写 + 菜单指令）
- 蓝图字段手动编辑 + 活态字段 AI 提议 + Diff 确认
- 大纲总纲 / 分卷 / 分章 / 节拍
- 节拍驱动的结对写作
- 概念抽卡（项目启动期的灵感卡片）
- Style Lab：单 TXT 深度分析 → 报告 / Voice Profile → 档案 → 项目挂载
- 章节 → 活态层记忆同步
- Provider 配置与 BYOK
- 一次性 setup 与 HttpOnly Session 登录

### ❌ 不在范围内

#### AI 能力层
- ❌ 多 Agent 编排（写手 Agent / 审校 Agent / 主编 Agent）
- ❌ 自动五维质量打分
- ❌ AI 味自动检测与消痕后处理
- ❌ 自动数值 / 战力 / 体系一致性校验
- ❌ 自动实体抽取 + 知识图谱构建

#### 数据与存储层
- ❌ 多 TXT 合并分析（目前只支持单 TXT）
- ❌ 独立证据账本（Evidence Ledger）持久化
- ❌ 多温区 RAG / 热暖冷记忆层
- ❌ 外部任务队列（当前是进程内 worker + DB lease）
- ❌ 启发式采样优化 / 超长文本专项分析策略（当前是段落聚合启发式）

#### 账号与权限层
- ❌ 多用户
- ❌ RBAC
- ❌ 团队协作
- ❌ 评论 / 协作编辑

#### UI 层
- ❌ 富文本所见即所得编辑器
- ❌ 多面板 IDE 式布局
- ❌ 主题定制
- ❌ 移动端适配（只做桌面端）
- ❌ 国际化（仅中文）

#### 运营层
- ❌ 计费 / 用量统计
- ❌ 审计日志 / 登录历史
- ❌ 用户反馈面板 / 公告系统
- ❌ 云部署脚本（Vercel / Render / Fly.io 一键部署）

---

## 五、性能与规模边界

### 单用户典型规模假设

- 项目数量：~10 本小说
- 每本小说章节：~500 章
- 每章字数：~3000 字
- Style Lab 样本：单个 TXT ~50 万字级别
- Style Analysis Job 并发：**不并发**——LLM 调用按用户配置串行，一次跑一个 Job

### 技术上的硬限制

- 每个 Style Analysis Job 对每个 chunk 的 LLM 调用通过 `PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY` 控制并发（默认较低，避免打爆 Provider rate limit）
- Prompt 组装时的 context size 由用户选用的模型决定——Persona 本身不截断 Prompt，大超了就让 LLM 报错

### 不做的优化

- ❌ 后端水平扩展 / 多实例（本就单用户，没意义）
- ❌ 前端 CDN / 图片优化（图片量级小）
- ❌ 数据库读写分离（单用户单实例）
- ❌ Redis 缓存（Prompt Caching 交给 LLM 厂商做）

---

## 六、安全边界

### 保护
- API Key 入库前加密，接口仅返回掩码
- 业务敏感字段用 `redaction.py` 提供的 `redact()` 做日志打码
- CORS 白名单通过 `Settings.cors_allowed_origins` 管控
- Session HttpOnly 防 XSS 盗 Cookie

### 不保护
- ❌ 本地 Postgres 的加密——作者自己负责磁盘加密
- ❌ 抗暴力破解——单用户登录不怕撞库
- ❌ CSRF Token——仅同源访问，SameSite Cookie 兜底
- ❌ 代码混淆 / 反调试——开源

---

## 七、部署边界

- **支持**：macOS / Linux 本机 `make dev` 起全套
- **支持**：docker-compose Postgres（不 docker 化 API / Web，因为开发期每天改）
- **支持**：单机服务器（用户可以把整套跑在自己的 VPS / 家用服务器）
- **不支持**：Kubernetes / 云原生部署脚本
- **不支持**：Windows（理论可以，但 Makefile + bash 脚本未适配）
- **不支持**：Serverless / Edge Runtime 部署（有本地文件 + 常驻 Worker 进程）

详见 [40 本地开发](../40-operations/40-local-dev-and-make.md)。

---

## 八、演进的可能扩展点（但当前不做）

这些是**可能的未来方向**，架构上预留了接入点，但 MVP 明确不做：

| 扩展点 | 预留位置 |
| --- | --- |
| 多 TXT 合并分析 | `style_analysis_jobs` 与 `style_sample_files` 是 1:N 关系（当前 1:1 使用） |
| 独立证据账本 | Style Analysis Pipeline 的 merge 节点目前直接生成报告，未来可拆出 Evidence Ledger 表 |
| 外部任务队列 | Worker 现在是进程内 + DB lease，换成 Celery / Dramatiq 只需实现同样接口 |
| Style Generator Graph（Critic Node） | `services/style_analysis_pipeline.py` 同模式可复用 |

**重要**：这些扩展点目前都是**空的**。不要依赖它们来做当前功能的架构决策。

---

## 下一篇

继续阅读 [03 MVP 现状与 Roadmap](./03-mvp-status-and-roadmap.md)，看每个功能**当前实际实现到什么程度**，哪些是"完整闭环"、哪些是"占位"。
