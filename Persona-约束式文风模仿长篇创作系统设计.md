# Persona：AI 约束式文风模仿长篇创作系统设计

> 文中带有 `（已完成）` 标记的条目，表示该部分已经在当前 `Persona/` 项目中完成实现。  
> 若标记为 `（已完成：占位）`，表示信息架构或页面入口已经落地，但核心业务流程尚未实现。
> 若标记为 `（已完成：MVP闭环）`，表示最小可用纵切已经打通，但距离长期规划中的完整形态仍有明显差距。
> 若标记为 `（已完成：深度分析闭环）`，表示已具备分阶段分析、结构化报告、风格摘要与风格母 Prompt 包，但仍未进入完整创作系统阶段。

---

## 一、系统定位：从“黑盒生成器”到“沉浸式工作台”

Persona 是一款支持 BYOK（自带 API Key）的约束式创作系统，当前产品体验仍以“管理员初始化 + 会话登录”的私有化使用路径为主，核心目标不是“一键写小说”，而是把大模型变成一个受审美约束、可被驯化的文字执行器。

它包含两个长期核心模块：

1. **风格实验室（Style Lab）**  
   将长篇小说样本（TXT）清洗、切片、采样并逆向工程，提炼为可复用的结构化风格档案。
2. **沉浸工作台（Zen Editor）**  
   提供极简、低干扰的创作白板，在写作过程中挂载风格档案，并通过快捷指令或 Ghost Text 调用 AI 进行严格约束的续写与改写。

系统坚持以下产品哲学：

1. **极简交互**：摒弃多面板 IDE 式布局，优先保证创作过程的沉浸感。
2. **私有化与极客向**：当前不提供公开注册入口，首次需由管理员完成初始化，用户自行维护模型 API Key。
3. **全局风格资产**：风格档案不强绑定某个项目，而是全局资产，可被不同创作项目重复挂载。

---

## 二、MVP 边界与当前进度

MVP 阶段不实现复杂的长篇记忆维护、知识图谱编辑器、富文本编辑器与多 Agent 全链路，而是优先做两层能力：

1. **基础框架：单用户登录系统、API Key 配置管理、项目管理的基础 CRUD。**  
   **（已完成）** 当前已在 `Persona/api` 与 `Persona/web` 中落地，包含：
   - 单用户初始化与登录
   - HttpOnly Session 鉴权
   - 核心业务资源按 `user_id` 做作用域隔离
   - OpenAI-compatible Provider 配置中心
   - 项目管理基础 CRUD、归档与恢复
   - 项目可挂载已保存的风格档案
   - 左侧工作台导航、`/setup`、`/login`、`/projects`、`/settings/models`、`/settings/account`

2. **风格实验室：TXT 上传 -> 输入判定 -> 分块分析 -> 聚合 -> 结构化报告 -> 风格摘要 -> 风格母 Prompt 包。**  
   **（已完成：深度分析闭环）** 当前已实现“单个 TXT -> 深度分析任务 -> 完整分析报告 -> 风格摘要 -> 风格母 Prompt 包 -> 风格档案 -> 项目挂载”的可用闭环，包含：
   - 单个 `.txt` 文件上传、文件类型与空文件校验
   - `style_sample_files`、`style_analysis_jobs`、`style_profiles` 三类核心资产
   - 原始 TXT 落本地磁盘、数据库保存元信息与任务状态
   - Worker claim 任务后进入 `preparing_input`，随后推进 `analyzing_chunks / aggregating / reporting / summarizing / composing_prompt_pack`
   - 基于 LangGraph 的分析流水线，使用 `thread_id = job.id` 做 checkpoint 持久化与失败后续跑
- 基于已配置 Provider/模型的真实 LLM 多阶段分析，采用 Markdown-First 纯文本输出契约，提升模型兼容性与输出稳定性
- 返回结果包 `analysis_meta / analysis_report_markdown / style_summary_markdown / prompt_pack_markdown`
   - `Style Lab` 页面支持只读完整报告、可编辑风格摘要、可编辑风格母 Prompt 包
   - 风格档案保存后支持再次覆盖更新当前摘要与 Prompt 包；项目挂载可在新建档案时选择，或在项目详情页单独维护
   - 任务 lease、心跳、尝试次数与陈旧任务恢复已落地，服务重启后会释放锁并恢复为可续跑任务
   当前仍未实现多 TXT 合并、外部任务队列、独立证据账本持久化、启发式采样优化与超长文本专项分析策略。

---

## 三、当前已落地的基础平台实现

### 1. 前后端分离基础骨架（已完成）

- **前端**：Next.js App Router
- **后端**：FastAPI + SQLAlchemy 2 + Alembic
- **数据库**：Postgres（`docker-compose.yml` 提供本地基线）
- **AI 接入层**：LangChain 当前用于 OpenAI-compatible 模型初始化、连通性测试、分阶段风格分析与风格母 Prompt 包生成
- **运行方式**：`Persona/README.md` 已提供启动、迁移、测试与构建说明

### 2. 单用户鉴权与初始化（已完成）

- 首次访问 `/` 会先跳转到 `/projects`，若未初始化再由工作台守卫重定向到 `/setup`
- 初始化时一次性完成：
  - 创建唯一管理员账号
  - 创建首个 Provider 配置
  - 写入会话 Cookie
- 登录后通过服务端 Session 访问受保护页面
- 不提供注册、多用户、忘记密码与 RBAC

### 3. BYOK 配置中心（已完成）

- 当前版本采用 **OpenAI-compatible** 统一配置模型，而不是按厂商拆分原生协议
- 支持多条 Provider 配置
- API Key 入库前加密，接口仅返回掩码
- 支持“测试连接”
- 若 Provider 被未归档项目或 Style Lab 资产（任务/风格档案）引用，则拒绝删除

### 4. 项目管理基础 CRUD（已完成）

- 支持项目创建、详情查看、编辑、归档、恢复
- 项目绑定默认 Provider 与默认模型
- `style_profile_id` 已升级为真实的风格档案外键，可直接挂载已保存的 `Style Profile`
- 默认列表不显示归档项目，可切换显示

### 5. 风格实验室深度分析纵切（已完成：深度分析闭环）

- 后端新增 `style_sample_files`、`style_analysis_jobs`、`style_profiles` 三张核心表
- 分析任务创建接口使用 `multipart/form-data`，要求显式选择 Provider，可选覆盖模型
- 原始 TXT 通过 `PERSONA_STORAGE_DIR` 落地到本地文件系统，数据库仅保存元信息、校验和与路径
- API 进程启动时会执行陈旧任务恢复；持续消费 `pending` 任务由独立 Worker 进程通过 lease claim 完成
- Style Lab 分析主流程已切换为 LangGraph，使用 SQLite/Postgres checkpointer 持久化 graph state
- chunk 分析使用 LangGraph `Send` fan-out 并发执行，并通过 `PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY` 控制并发上限
- LLM 直接输出 Markdown 纯文本契约（Markdown-First），具有极高的模型兼容性
- 后端任务结果已稳定为 `analysis_meta / analysis_report_markdown / style_summary_markdown / prompt_pack_markdown`
- 风格档案保存逻辑已从“一次性草案入库”升级为“只读报告 + 可覆盖摘要/Prompt 包”
- 前端 `/style-lab` 工作页已支持：上传、任务列表、阶段反馈、完整分析报告查看、风格摘要编辑、风格母 Prompt 包编辑、保存风格档案、挂载项目

### 6. 前端工作台路由（已完成）

- `/setup` 初始化页
- `/login` 登录页
- `/projects` 项目列表页
- `/projects/new` 新建项目页
- `/projects/[id]` 项目详情与编辑页
- `/settings/models` Provider 配置页
- `/settings/account` 账户页
- `/style-lab` 风格实验室深度分析工作页  
  **（已完成：深度分析闭环）**

---

## 四、总体架构设计

长期来看，系统采用**解耦的多图微工作流（Decoupled Micro-Workflows）**与**共享记忆中枢**架构。

### 1. 当前落地基线

- 前端通过 REST API 与后端通信，并对 Style Lab 深度分析任务做轮询查询
- 后端以 Postgres 为统一持久化中心，并结合本地文件存储保存原始 TXT 样本
- LangChain 当前承担模型适配、Provider 连通性测试与结构化输出封装；LangGraph 承担 Style Lab 分析流程编排
- 独立 Worker 进程负责 claim/lease、心跳更新与分析结果写回；API 进程在启动时执行一次陈旧任务恢复
- Checkpointer 支持从数据库 URL 推导 SQLite/Postgres，并可通过 `PERSONA_STYLE_ANALYSIS_CHECKPOINT_URL` 显式覆盖

### 2. 长期目标架构

- 前端触发不同的创作、分析、审校与记忆维护流程
- 各子流程由独立 LangGraph 子图负责
- 各子图共享：
  - **Postgres 抽象出的可编辑知识图谱（Editable KG）**
  - **Milvus / 向量库中的情节记忆**
  - **工作记忆 / Scratchpad / 章节上下文**

也就是说，基础平台解决“账号、配置、项目与入口”，后续 AI 核心能力则叠加在这层之上，而不是把业务 CRUD 混进 Agent 图里。

---

## 五、文风提取与生成工程化（Style Engineering）

文风模仿的真正难点不在单次 Prompt，而在于如何把百万字样本蒸馏成可复用、可注入、可评估的风格约束。

### 1. 长文本风格蒸馏流水线

当前已落地的是一个**LangGraph 驱动的深度分析流水线**：

- 上传单个 TXT 后，系统先把原文落到本地存储，再创建数据库任务记录
- Worker 先做输入判定与切片，再把 `thread_id = job.id` 的状态送入 LangGraph
- Graph 节点当前为 `prepare_input -> analyze_chunks(map fan-out) -> merge_chunks -> build_report -> build_summary -> build_prompt_pack -> persist_result`
- `analyze_chunks` 使用并发 map-reduce，局部 chunk 结果通过 reducer 聚合后再进入全局报告阶段
- 所有 LLM 节点均采用 Markdown-First 提示词策略，通过明确的 Markdown 标题层级和指令来约束章节完整性
- 当前切片仍采用段落聚合的启发式策略，但最终产物已稳定为“分析元信息 + Markdown 报告 + Markdown 风格摘要 + Markdown 风格母 Prompt 包”
- 完整分析报告为只读审阅层；风格摘要和 Prompt 包为可编辑层
- 风格档案保存后，项目侧后续消费的是当前风格资产上的 `prompt_pack`
- checkpointer 会在失败后从未完成节点续跑；job lease 与 `attempt_count` 负责避免重复消费和无限重试
- 这套实现已经把 LangGraph、结构化输出和任务恢复纳入生产路径，但尚未进入多 TXT / 多 Agent 的完整长期形态

#### 模块 1：样本清洗与分块（Chunking）

- 接收 `.txt` 文件
- 清理乱码、版权声明、无意义字符
- 按章节或固定长度切成多个 Chunks

#### 模块 2：局部特征采样（Sampling）

- 不对全部文本块逐个做昂贵分析
- 采用启发式规则或随机采样，抽出最具代表性的片段
- 例如分别采样对白、环境描写、动作场景

#### 模块 3：多维特征提取（LLM Analysis）

重点提取：

- **词汇习惯**：高频词、虚词偏好、稀有表达
- **句法节奏**：长短句比例、断句方式、排比与并列结构
- **叙事视角与距离**：第一人称沉浸、第三人称有限全知等
- **对白模式**：语气词、角色说话长短、文白程度

#### 模块 4：特征聚合与 Prompt 生成（Aggregation & Generation）

- 将多轮零散分析结果再次聚合
- 输出全局风格档案
- 生成后续可直接注入写作工作流的系统 Prompt、分类 Prompt 与 few-shot 样本

### 2. LangGraph 中的当前形态与长期形态

#### StyleAnalyzerGraph（当前已落地）

- **Prepare Node**：校验输入状态并准备 chunk map
- **Analyze Chunk Node**：并发提取 chunk 局部特征
- **Merge Node**：去重、合并、保留弱判断与说话人差异
- **Report / Summary / PromptPack Nodes**：输出完整报告、可编辑摘要与生成 Prompt 包
- **Persist Result Node**：回填 `analysis_meta`

#### StyleGeneratorGraph（长期规划）

- **Context Builder Node**：组装剧情上下文与风格约束
- **Draft Node**：按超参数生成初稿
- **Critic Node**：做高频词、忌讳词、句长分布与风格偏差校验

---

## 六、核心资产定义：风格档案（Style Profile）

风格提取的最终产物不是一段松散提示词，而是一个可以入库、被多个项目复用、并被工作流系统化调用的结构化对象。

当前数据库中实际落地的风格档案对象为“报告 + 摘要 + Prompt 包”的组合体；报告和中间分析结构均采用 Markdown-First 策略，落库与 API 契约均为 Markdown 纯文本，形如下面的结构：

```json
{
  "id": "uuid",
  "source_job_id": "uuid",
  "provider_id": "uuid",
  "model_name": "gpt-4.1-mini",
  "source_filename": "射雕英雄传.txt",
  "style_name": "金庸武侠风",
  "analysis_report_markdown": "# 1. 执行摘要\n\n...\n\n# 3. 详细维度分析\n\n## 3.1 词汇习惯\n...",
  "style_summary_markdown": "# 风格定位\n整体语言古雅克制，动作场面偏短句，节奏紧凑。\n\n## 核心特征\n- 短句推进\n- 冷感意象\n...",
  "prompt_pack_markdown": "# System Prompt\n以克制、古雅、动作精准为核心约束进行生成。\n\n## 场景 Prompt\n### 对白\n对白尽量简短，不要现代口头禅。\n..."
}
```

也就是说，当前实现已经把“可复用风格资产”落成真实数据模型，并把“分析结果”和“写作调用 Prompt”显式拆层；但它仍然是简化版深度分析实现，未来仍可继续扩展独立证据账本、更多约束维度与更稳定的长文本聚合策略。

未来在 Zen Editor 中，当用户触发“续写”或“改写”时，系统会把：

- `prompt_pack_markdown` 提取出的系统提示词
- `prompt_pack_markdown` 提取出的场景特定约束
- `prompt_pack_markdown` 提取出的 Few-shot 示例

与当前项目上下文一起组装成最终请求。

---

## 七、长文本记忆与全局连贯性（Long-form Memory）

在长篇创作阶段，系统计划采用增强三层记忆架构：

### 1. 工作记忆（Working Memory）

- 仅保留当前细纲与最近 3-5 章
- 直接注入大模型上下文窗口
- 保证局部连贯与当前写作可控性

### 2. 草稿本缓存（Scratchpad）

- 位于工作记忆与长期记忆之间
- 每次场景生成后记录关键事实和状态变化
- 例如：角色受伤、物品获得、关系变化

### 3. 语义记忆：可编辑知识图谱（Editable Semantic KG）

- 基于 Postgres 抽象实体-关系图谱
- 节点：角色、地点、物品、专属文风约束
- 边：人物关系、阵营、归属、状态变化
- 伏笔追踪：Open Loops / Resolved Loops

### 4. 情节记忆：Episodic Memory

- 将历史章节切块后向量化存储
- 每次生成前按角色、地点、事件召回历史片段
- 与 KG 的局部子图一起参与上下文构建

---

## 八、多 Agent 工作流编排（Multi-Agent Orchestration）

长期规划中，不同阶段由不同 Agent 或子图负责：

- **IdeaGraph**：世界观工坊
- **OutlineGraph**：大纲推演
- **DetailOutlineGraph**：细纲拆解
- **DraftingGraph**：正文执笔
- **ReviewGraph**：质检与风格校验
- **UpdateGraph**：将 Scratchpad 事实写回持久化图谱

这套编排目前尚未实现，但其运行依赖的基础平台已经具备：

- 用户入口
- 项目容器
- Provider 配置
- Postgres 基线
- 前端导航与 Style Lab 工作页

---

## 九、人机协同与质量控制（Co-Creation Engine）

系统的理想形态不是“全自动写作”，而是高强度的人机协同。

### 1. 全链路断点（HITL）

- 在大纲、细纲、正文等关键阶段设置 `interrupt`
- 用户可：
  - Approve
  - Reject
  - Direct Edit

### 2. 图谱编辑器（KG Editor）

- 让用户直接修改角色关系和剧情事实
- 替代脆弱的长 Prompt 修正
- 保持长期可控性与一致性

### 3. 行内协作（Inline Copilot）

- Tab 补全
- 划词改写
- `/` 指令菜单
- 风格挂载状态可见

### 4. 质量控制面板（QC Dashboard）

- 风格贴合度
- 连贯性警报
- 伏笔收束提示

---

## 十、错误处理与测试策略

### 1. 长期 AI 工作流层

- 图级异常捕获与指数退避
- Critic Node 拒绝明显偏离风格的结果
- 用户直接修改优先于 AI 状态
- 建立固定回归集，迭代 Prompt 与模型时必须复跑

### 2. 当前基础平台层（已完成）

当前项目已完成的验证包括：

- 后端 pytest 回归：初始化、登录、登出、Session 校验、Provider CRUD、Provider 测试、项目 CRUD、归档/恢复、Alembic 迁移  
  **（已完成）**
- 后端 Style Lab 回归：任务创建、非法文件与空文件校验、输入判定、LangGraph 并发分块分析、checkpoint 续跑、结构化报告/摘要/Prompt 包产出、任务 lease 恢复、风格档案保存与覆盖更新、项目挂载  
  **（已完成：深度分析闭环）**
- 前端组件与页面测试：初始化页、登录页、项目页、Provider 配置页、工作台壳层  
  **（已完成）**
- 前端 Style Lab 与项目挂载测试：上传表单、阶段反馈、完整报告展示、风格摘要编辑、Prompt 包编辑、风格档案创建/覆盖更新、项目风格档案选择  
  **（已完成：深度分析闭环）**
- 前端生产构建验证：`pnpm build`  
  **（已完成）**

---

## 十一、Roadmap

### Phase 1：基础平台 + 风格实验室

- 基础框架  
  **（已完成）**
- Style Lab 深度分析结果包：输入判定、分块分析、结构化报告、风格摘要、风格母 Prompt 包  
  **（已完成：深度分析闭环）**
- Style Lab 的下一阶段增强：多 TXT 合并、独立证据账本持久化、超长文本批处理、采样/聚合质量升级、外部任务队列化  
  尚未开始

### Phase 2：Zen Editor

- 极简编辑器
- Ghost Text 续写
- 划词改写
- 风格档案注入

### Phase 3：Memory

- 后台维护角色状态与时间线
- 自动拼装长期上下文
- 将创作从“单次调用”提升为“持续写作系统”

---

## 十二、结论

当前 `Persona` 已完成的是**产品化基础平台层 + Style Lab 深度分析闭环**，但仍不是完整的 AI 创作系统：

- 基础平台已经具备真实可运行的前后端与数据库骨架
- 单用户初始化、登录、Provider 配置、项目 CRUD 已经可用
- Style Lab 已完成单 TXT 深度分析、后台任务、完整分析报告、风格摘要、风格母 Prompt 包、风格档案入库与项目挂载
- 长期记忆、知识图谱、Milvus、Zen Editor、LangGraph 多图工作流仍处于设计完成、实现待续阶段

因此，当前最合理的下一步也不再是“从零启动 Style Lab”，而是基于已有深度分析闭环继续进入：

1. Style Lab 的超长文本工程化能力、任务恢复能力与证据层增强
2. 风格分析质量、多轮聚合和独立证据账本的进一步完善
3. Zen Editor 与风格母 Prompt 包注入的真实创作入口

> 核心哲学不变：大模型不是小说家，而是一个可训练、可约束、可审校的风格执行器。
