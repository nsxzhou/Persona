# AI 约束式文风模仿长篇创作系统 - 架构设计与方案探索

**日期**: 2026-04-07
**主题**: AI 约束式文风模仿长篇创作系统
**核心定位**: 深度人机协同（Copilot）的长篇小说创作工作流系统，基于 LangGraph、可编辑知识图谱（Editable KG）与 Milvus，实现高保真文风约束与全局记忆连贯。

---

## 1. 总体架构设计
系统采用**解耦的多图微工作流（Decoupled Micro-Workflows）**结合**共享记忆中枢**架构。摒弃单一庞大的状态机，将小说的长周期创作生命周期拆解为多个独立、可插拔的 LangGraph 子图。前端通过与系统交互，触发不同的子图执行，各个子图之间通过基于 Postgres 抽象的**可编辑知识图谱（Editable KG）**和向量数据库（Milvus）共享状态与上下文。

---

## 2. 核心模块设计

### 模块一：文风提取与生成的工程化 (Style Engineering)
将现有的 `ANALYZE-GENERATE` 规则体系彻底转化为自动化流水线，解决长文本解析与风格对齐问题。

#### 2.1 StyleAnalyzerGraph (文风指纹提取)
*   **Ingest Node (切片)**: 将超长语料按 4000 字或 40 章的策略切分为分析单元（Analysis Unit）。
*   **Extract Node (Map)**: 并发处理各个分析单元，严格扫描词汇、句法、标点、缺陷等 12 个维度的风格特征。
*   **Merge Node (Reduce)**: 合并、去重同义特征，并按说话人（Speaker）进行隔离。
*   **Report Node**: 产出人类可读分析报告及机器可读的 JSON 格式 `StyleConstraintSummary`（文风约束摘要）。

#### 2.2 StyleGeneratorGraph (约束式生成与自校验)
*   **Context Builder Node**: 动态组装当前剧情上下文与 `StyleConstraintSummary`。
*   **Draft Node**: 基于超参数（`style_intensity`, `defect_multiplier`, `jump_multiplier`）生成初稿。
*   **Critic Node**: 廉价快速的 LLM 或正则规则检查节点，校验高频词、忌讳词及句长分布。不达标则触发内部重试（Self-Correction）。

### 模块二：长文本记忆与全局连贯性 (Long-form Memory)
采用基于 LIGHT 框架的**增强三层记忆架构 (Enhanced Hierarchical Memory)**，彻底解决百万字级别的设定遗忘与逻辑断层问题。

*   **工作记忆 (Working Memory)**: 仅保留当前细纲与最近 3-5 章内容，注入 LLM Context Window，保证局部连贯。
*   **草稿本缓存 (Scratchpad - *新增*)**: 在工作记忆与长期记忆之间增加暂存推理区。每次场景生成后，AI 自动在 Scratchpad 中记录“核心事实与状态变化”（如：李四重伤、主角获得宝剑），极大缓解了 LLM 在长上下文下的推理能力衰减问题。
*   **语义记忆：可编辑知识图谱 (Editable Semantic KG - *升级*)**:
    *   将底层关系型数据库（Postgres）抽象为“实体-关系”图谱结构。
    *   **节点 (Nodes)**：角色档案（含专属文风约束）、地点、物品。
    *   **边 (Edges)**：人物关系、物品归属、阵营状态。
    *   **伏笔追踪器**: 记录 Open Loops（未收束）与 Resolved Loops（已收束）。
*   **情节记忆 (Episodic Memory - Milvus)**:
    *   将历史生成章节切块并向量化存储。
    *   **GraphRAG 工作流**: 每次生成新场景前，根据角色和地点不仅从 Milvus 召回历史片段，同时从 KG 召回相关角色的“局部子图（Sub-graph）”。

### 模块三：多 Agent 工作流编排 (Multi-Agent Orchestration)
基于 LangGraph 编排长篇网文的工业化生产流水线，各 Agent 职责更聚焦。

*   **IdeaGraph (世界观工坊)**: `WorldBuilderAgent` 负责与用户脑暴，产出初始知识图谱节点与简介。
*   **OutlineGraph (大纲推演室)**: `OutlineAgent` 根据起承转合结构生成多层级大纲。
*   **DetailOutlineGraph (细纲拆解台)**: `DetailOutlineAgent` 将单章拆解为多个具体场景指令（Scene Prompts）。
*   **DraftingGraph (正文执笔区)**: `WriterAgent` 加载文风约束、局部子图（KG）与记忆片段（Milvus）逐场景生成正文，并将状态变化推理写入 **Scratchpad**。
*   **ReviewGraph (质检部)**: `EditorAgent` 负责逻辑查错与风格校验。若有冲突则带上 Feedback 路由回执笔区重写。
*   **UpdateGraph (图谱维护部 - *新增*)**: `GraphUpdaterAgent` 负责在章节经人工确认通过后，读取 Scratchpad 中的暂存事实，自动将其转化为持久化的图谱更新操作（Create/Update Node, Add Edge）。

### 模块四：人机协同与质量控制 (Co-Creation Engine)
系统的灵魂层，确保 AI 充当辅助“副驾驶”，人类掌握最高决策权。

*   **全链路断点 (HITL)**: 在流水线的每一阶段（大纲、细纲、正文）设置 `__interrupt__`。用户可选择 Approve（通过）、Reject（打回）或 Direct Edit（手改，存为 Source of Truth）。
*   **图谱编辑器 (KG Editor - *核心增强*)**: 
    *   基于论文研究，提供直观的图谱可视化编辑界面。用户若发现剧情偏离，无需复杂 Prompt，直接在图谱中修改关系连线（如：将“敌对”改为“结盟”），AI 下次生成时自动遵循新图谱逻辑，提供极强、极稳定的上帝视角控制感。
*   **行内协作 (Inline Copilot)**: 支持“写半句按 Tab 补全（带风格约束）”、“框选段落注入文风”。
*   **质量控制面板 (QC Dashboard)**: 侧边栏实时展示当前文本的：
    *   **风格贴合度探针 (Style Adherence Score)**
    *   **连贯性警报器 (Continuity Warnings)** (如：角色死亡却再次出场)
    *   **伏笔收束提示**

---

## 3. 错误处理与测试策略
*   **图级自愈**: 所有生成节点默认带异常捕获与重试机制（指数退避）。若生成严重偏离文风，`Critic Node` 会拒绝放行，最多重试 3 次后抛出异常给用户。
*   **数据隔离**: 用户的直接修改优先于任何 AI 状态，系统不会覆盖人类认定的 Source of Truth。
*   **回归测试**: 根据 8 周计划，建立 50+ 条的固定回归集（包含复杂风格的提取、极易冲突的逻辑场景）。每次迭代 Prompt 或切换 LLM 必须跑通回归测试，确保功能（尤其是文风保真度）不倒退。
