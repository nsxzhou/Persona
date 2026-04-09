# Persona：AI 约束式文风模仿长篇创作系统设计

> 文中带有 `（已完成）` 标记的条目，表示该部分已经在当前 `Persona/` 项目中完成实现。  
> 若标记为 `（已完成：占位）`，表示信息架构或页面入口已经落地，但核心业务流程尚未实现。

---

## 一、系统定位：从“黑盒生成器”到“沉浸式工作台”

Persona 是一款支持 BYOK（自带 API Key）的单用户约束式创作系统，核心目标不是“一键写小说”，而是把大模型变成一个受审美约束、可被驯化的文字执行器。

它包含两个长期核心模块：

1. **风格实验室（Style Lab）**  
   将长篇小说样本（TXT）清洗、切片、采样并逆向工程，提炼为可复用的结构化风格档案。
2. **沉浸工作台（Zen Editor）**  
   提供极简、低干扰的创作白板，在写作过程中挂载风格档案，并通过快捷指令或 Ghost Text 调用 AI 进行严格约束的续写与改写。

系统坚持以下产品哲学：

1. **极简交互**：摒弃多面板 IDE 式布局，优先保证创作过程的沉浸感。
2. **私有化与极客向**：仅支持单用户，首次访问时由管理员初始化，用户自行维护模型 API Key。
3. **全局风格资产**：风格档案不强绑定某个项目，而是全局资产，可被不同创作项目重复挂载。

---

## 二、MVP 边界与当前进度

MVP 阶段不实现复杂的长篇记忆维护、知识图谱编辑器、富文本编辑器与多 Agent 全链路，而是优先做两层能力：

1. **基础框架：单用户登录系统、API Key 配置管理、项目管理的基础 CRUD。**  
   **（已完成）** 当前已在 `Persona/api` 与 `Persona/web` 中落地，包含：
   - 单用户初始化与登录
   - HttpOnly Session 鉴权
   - OpenAI-compatible Provider 配置中心
   - 项目管理基础 CRUD、归档与恢复
   - 左侧工作台导航、`/setup`、`/login`、`/projects`、`/settings/models`、`/settings/account`
   - `Style Lab` 页面占位与信息架构入口

2. **风格实验室：TXT 上传 -> 切片 -> 特征采样 -> LLM 抽取 -> 聚合生成结构化 Prompt。**  
   当前尚未实现核心工作流，仅完成入口预留。  
   **（已完成：占位）** `Style Lab` 页面与后续扩展架构已建立，但样本上传、任务调度与风格提炼链路尚未开始。

---

## 三、当前已落地的基础平台实现

### 1. 前后端分离基础骨架（已完成）

- **前端**：Next.js App Router
- **后端**：FastAPI + SQLAlchemy 2 + Alembic
- **数据库**：Postgres（`docker-compose.yml` 提供本地基线）
- **AI 接入层**：LangChain 仅用于 OpenAI-compatible 模型初始化与连通性测试
- **运行方式**：`Persona/README.md` 已提供启动、迁移、测试与构建说明

### 2. 单用户鉴权与初始化（已完成）

- 首次访问进入 `/setup`
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
- 若 Provider 被未归档项目引用，则拒绝删除

### 4. 项目管理基础 CRUD（已完成）

- 支持项目创建、详情查看、编辑、归档、恢复
- 项目绑定默认 Provider 与默认模型
- `style_profile_id` 已预留，为下一阶段挂接风格档案做准备
- 默认列表不显示归档项目，可切换显示

### 5. 前端工作台路由（已完成）

- `/setup` 初始化页
- `/login` 登录页
- `/projects` 项目列表页
- `/projects/new` 新建项目页
- `/projects/[id]` 项目详情与编辑页
- `/settings/models` Provider 配置页
- `/settings/account` 账户页
- `/style-lab` 风格实验室占位页  
  **（已完成：占位）**

---

## 四、总体架构设计

长期来看，系统采用**解耦的多图微工作流（Decoupled Micro-Workflows）**与**共享记忆中枢**架构。

### 1. 当前落地基线

- 前端通过 REST API 与后端通信
- 后端以 Postgres 为统一持久化中心
- LangChain 当前仅承担模型适配职责
- LangGraph 尚未用于生产流程，但已作为后续工作流编排主框架预留

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

### 2. LangGraph 中的长期形态

#### StyleAnalyzerGraph

- **Ingest Node**：切片
- **Extract Node**：并发提取多维风格特征
- **Merge Node**：去重、合并、按说话人隔离
- **Report Node**：输出人类可读报告与机器可读 `StyleConstraintSummary`

#### StyleGeneratorGraph

- **Context Builder Node**：组装剧情上下文与风格约束
- **Draft Node**：按超参数生成初稿
- **Critic Node**：做高频词、忌讳词、句长分布与风格偏差校验

---

## 六、核心资产定义：风格档案（Style Profile）

风格提取的最终产物不是一段松散提示词，而是一个可以入库、被多个项目复用、并被工作流系统化调用的结构化对象。

```json
{
  "profile_id": "uuid",
  "style_name": "金庸武侠风",
  "source_text": "射雕英雄传.txt",
  "global_system_prompt": "你现在是一位武侠小说大师，你的文风特点是：句式简短有力，动词使用极其精准，极少使用华丽的形容词堆砌...",
  "dimensions": {
    "vocabulary": ["高频词1", "高频词2"],
    "rhythm": "长短句结合，动作场面多用四字短句",
    "perspective": "第三人称有限全知"
  },
  "specific_prompts": {
    "dialogue": "在生成对白时，请注意：人物语言应带有文言色彩，少用现代白话...",
    "action": "在描写动作时，侧重于招式的拆解和气机的流动..."
  },
  "few_shot_examples": [
    {
      "type": "environment",
      "text": "风雪满天，破庙中只余一炉残火..."
    },
    {
      "type": "dialogue",
      "text": "郭靖大怒，喝道：‘你这贼子，今日教你有来无回！’"
    }
  ]
}
```

未来在 Zen Editor 中，当用户触发“续写”或“改写”时，系统会把：

- `global_system_prompt`
- 相关 `specific_prompts`
- `few_shot_examples`

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
- 前端导航与占位路由

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
- 前端组件与页面测试：初始化页、登录页、项目页、Provider 配置页、工作台壳层  
  **（已完成）**
- 前端生产构建验证：`pnpm build`  
  **（已完成）**

---

## 十一、Roadmap

### Phase 1：基础平台 + 风格实验室

- 基础框架  
  **（已完成）**
- Style Lab 上传、切片、采样、聚合与风格档案生成  
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

当前 `Persona` 已完成的是**产品化基础平台层**，而不是完整的 AI 创作系统：

- 基础平台已经具备真实可运行的前后端与数据库骨架
- 单用户初始化、登录、Provider 配置、项目 CRUD 已经可用
- 风格实验室、长期记忆、知识图谱、Milvus、LangGraph 多图工作流仍处于设计完成、实现待续阶段

因此，当前最合理的下一步不是继续改基础框架，而是直接在已有平台之上进入：

1. Style Lab 文本上传与异步任务
2. 风格提取流水线
3. 风格档案入库与项目挂载

> 核心哲学不变：大模型不是小说家，而是一个可训练、可约束、可审校的风格执行器。
