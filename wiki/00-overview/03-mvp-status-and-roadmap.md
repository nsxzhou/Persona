# 03 MVP 现状与 Roadmap

**实事求是地列出每个功能当前的实现程度**——完整闭环、MVP 闭环、深度分析闭环、占位、未开始。

本章是快速扫盲：接手任务前先在这里确认"你要改的功能当前是什么成熟度"，避免把占位逻辑当完整功能来改。

---

## 一、状态标记约定

沿用 `Persona-约束式...设计.md` 的标记体系：

| 标记 | 含义 |
| --- | --- |
| ✅ **已完成** | 功能完整落地，主路径跑通并有测试覆盖 |
| 🔁 **已完成：MVP 闭环** | 最小可用纵切已打通，但距离长期规划仍有明显差距 |
| 🧪 **已完成：深度分析闭环** | Style Lab 专项——已具备分阶段分析、结构化报告、Voice Profile，但未进入完整创作系统阶段 |
| 🏗️ **已完成：占位** | 信息架构或页面入口已落地，但核心业务流程尚未实现 |
| ⏳ **未开始** | 代码里没有任何实质性痕迹 |

---

## 二、功能矩阵

### 基础平台层

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| 单用户初始化（`/setup`） | ✅ | `web/app/setup/page.tsx`、`api/app/api/routes/setup.py` |
| 单用户登录（`/login`） | ✅ | `web/app/login/page.tsx`、`api/app/api/routes/auth.py` |
| HttpOnly Session 鉴权 | ✅ | `api/app/core/security.py`、`api/app/api/deps.py` |
| 业务资源按 `user_id` scope 隔离 | ✅ | 所有 service / repository |
| 路由守卫（工作区服务端重定向 + setup/login 客户端跳转） | ✅ | `web/app/(workspace)/layout.tsx`、`web/components/route-guards.tsx` |

### Provider 配置（BYOK）

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| Provider CRUD（多条配置） | ✅ | `web/app/(workspace)/settings/models/page.tsx`、`api/app/api/routes/provider_configs.py` |
| API Key 加密入库 + 掩码返回 | ✅ | `api/app/services/provider_configs.py` |
| 测试连接（Provider 连通性校验） | ✅ | `api/app/services/llm_provider.py` |
| 防删除被引用的 Provider | ✅ | service 层校验 |

### 项目管理

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| 项目 CRUD | ✅ | `web/components/projects-page-view.tsx`、`api/app/api/routes/projects.py` |
| 归档 / 恢复 | ✅ | |
| 挂载风格档案（`style_profile_id`） | ✅ | 新建项目、项目表单和工作台设置页都可操作 |
| 挂载情节档案（`plot_profile_id`） | ✅ | 新建项目、项目表单和工作台设置页都可操作 |
| 默认 Provider + 默认模型绑定 | ✅ | `ProjectForm` 与 `SettingsTab` |
| 项目导出 txt / epub | ✅ | `web/components/export-project-dialog.tsx`、`api/app/services/export.py` |

### 章节与大纲

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| 章节树按大纲同步 + 正文更新 | ✅ | `web/components/chapter-tree.tsx`、`api/app/api/routes/project_chapters.py` |
| 总纲 `outline_master` 编辑 | ✅ | `projects` 表字段 |
| 分卷 / 分章细纲 `outline_detail` | ✅ | `web/components/outline-detail-tab.tsx`、`lib/outline-parser.ts`、`api/app/services/outline_parser.py` |
| 节拍面板 + 节拍生成 | ✅ | `web/components/beat-panel.tsx`、`hooks/use-beat-generation.ts` |
| 节拍驱动的结对写作（Beat-Driven） | ✅ | Zen Editor 流程 |
| 大纲模板与生成 | ✅ | `web/lib/bible-templates.ts` 及相关 prompt |

### 圣经（Bible）

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| 蓝图字段编辑（5 项） | ✅ | `ProjectBible` 的 `inspiration` / `world_building` / `characters` / `outline_master` / `outline_detail` |
| 活态字段（2 项）AI 提议 | ✅ | `ProjectBible` 的 `runtime_state` / `runtime_threads` |
| 圣经 Diff Dialog（AI 提议 vs 当前）| ✅ | `web/components/bible-diff-dialog.tsx` |
| 圣经字段元数据增强 | ✅ | `web/lib/bible-fields.ts`、`api/app/core/bible_fields.py` |
| 圣经模板 | ✅ | `web/lib/bible-templates.ts`、概念生成 prompt |

### Zen Editor

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| 极简编辑器（原生 textarea + 预览）| ✅ | `web/components/zen-editor-view.tsx` |
| 编辑器菜单（续写 / 改写 / 压缩等指令） | ✅ | `web/components/editor-novel-menu.tsx` |
| 自动保存 | ✅ | `web/hooks/use-editor-autosave.ts` |
| 续写补全 | ✅ | `web/hooks/use-editor-completion.ts` |
| SSE 流式生成 | ✅ | `web/hooks/use-streaming-text.ts`、`api/app/api/sse.py` |
| Markdown 预览 | ✅ | `web/components/markdown-preview.tsx` |
| 划词改写（Cmd+K Inline Copilot）| ✅ | 菜单指令集成 |
| **Ghost Text 自动续写**（实时补全）| ⏳ | **未开始** |

### 概念抽卡（Concept Gacha）

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| 概念抽卡页面 | ✅ | `web/app/(workspace)/projects/new/page.tsx`、`web/components/concept-gacha-page.tsx` |
| 3 张差异化概念卡 | ✅ | `/api/v1/projects/generate-concepts` + `ConceptGachaPage` |
| 标题与简介规则约束 | ✅ | `api/app/prompts/concept.py` 的概念生成 prompt 与前端 Markdown 解析 |

### Style Lab（风格实验室）

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| TXT 上传 + 文件/空文件校验 | 🧪 | `api/app/services/style_analysis_jobs.py` |
| `style_sample_files` / `style_analysis_jobs` / `style_profiles` 三表 | 🧪 | `api/app/db/models.py` |
| 原始 TXT 落地本地 + DB 存元信息 | 🧪 | |
| Worker 进程 + lease claim + 心跳 | 🧪 | `api/app/services/style_analysis_worker.py`、`api/app/worker.py` |
| LangGraph 分析管道（prepare → analyze → merge → report → summary → prompt pack → persist） | 🧪 | `api/app/services/style_analysis_pipeline.py` |
| Chunk 并发分析（`Send` fan-out）| 🧪 | 可通过 `PERSONA_STYLE_ANALYSIS_CHUNK_MAX_CONCURRENCY` 配 |
| Checkpointer 续跑（SQLite/Postgres）| 🧪 | `api/app/services/style_analysis_checkpointer.py` |
| Markdown-First 输出契约 | 🧪 | `api/app/prompts/style_analysis.py`、`style_analysis_llm.py` |
| 阶段反馈 + 实时增量日志拉取 | 🧪 | 前端 `/style-lab` 任务列表展示 |
| 手动暂停 / 恢复任务 | 🧪 | |
| 完整分析报告只读审阅 | 🧪 | `style-lab-wizard-report-step.tsx` |
| Voice Profile可编辑 | 🧪 | `style-lab-wizard-summary-step.tsx` |
| 保存风格档案 + 覆盖更新 | 🧪 | `api/app/services/style_profiles.py` |
| 项目挂载风格档案 | 🧪 | |
| **多 TXT 合并分析** | ⏳ | 数据模型已留 1:N，但实际走的是 1:1 |
| **独立证据账本持久化** | ⏳ | |
| **超长文本专项分析策略** | ⏳ | 当前只有段落聚合启发式 |
| **外部任务队列化（Celery 等）** | ⏳ | 现在是进程内 + DB lease |

### Plot Lab（情节实验室）

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| Plot Lab Dashboard / Wizard / Profile UI | ✅ | `web/app/(workspace)/plot-lab/page.tsx`、`web/app/(workspace)/plot-lab/[id]/page.tsx`、`web/components/plot-lab-wizard-view.tsx`、`web/components/plot-lab-profile-view.tsx` |
| `plot_sample_files` / `plot_analysis_jobs` / `plot_profiles` 三表 | ✅ | `api/app/db/models.py` |
| Plot 分析管道（sketch → skeleton → report → summary → prompt pack） | ✅ | `api/app/services/plot_analysis_pipeline.py` |
| Plot 任务暂停 / 恢复 / stale recovery 状态机 | ✅ | `api/app/services/plot_analysis_worker.py`、`api/app/main.py` |
| Plot Worker 默认启动集成 | ✅ | `api/app/worker.py`、`Makefile` |
| Plot Lab 默认本地端到端闭环 | ✅ | `make dev` 下可由统一 Worker 直接消费任务 |

### 记忆同步（Memory Sync）

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| 章节 → 活态层回灌按钮 | ✅ | `web/components/memory-sync-button.tsx` |
| 章节记忆同步 hook | ✅ | `web/hooks/use-chapter-memory-sync.ts` |
| Diff 计算与展示 | ✅ | `web/lib/diff-utils.ts`、`bible-diff-dialog.tsx` |
| 自动同步触发（短片段与整章两条路径） | ✅ | `use-chapter-memory-sync.ts`、`use-editor-completion.ts` |

### LLM 管道与上下文

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| 上下文组装（蓝图 + 活态 + 前 3 章 + 当前章大纲） | ✅ | `api/app/services/context_assembly.py` |
| Prompt Caching 策略 | ✅ | 靠"前段不变 + 后段动态"的自然 cache key |
| 运行时 Prompt 模板（Novel Workflow / Style / Plot） | ✅ | `api/app/prompts/` 下的专职模块、`api/app/prompts/style_analysis.py`、`api/app/prompts/plot_analysis.py` |
| Length Presets（生成长度预设） | ✅ | `api/app/core/length_presets.py`、`web/lib/length-presets.ts` |
| Redaction（日志脱敏） | ✅ | `api/app/core/redaction.py` |
| SSE 流式响应 + 错误恢复 | ✅ | `api/app/api/sse.py`、`web/lib/sse.ts` |

### 运维与工程

| 功能 | 状态 | 入口 |
| --- | --- | --- |
| `make dev` / `make status` / `make stop` | ✅ | `Makefile` |
| 端口检测（8000 / 3000） | ✅ | Makefile 逻辑 |
| Postgres 容器自动启停 | ✅ | `docker-compose.yml` |
| Alembic 迁移 | ✅ | `api/alembic/` |
| 后端 pytest 回归 | ✅ | `api/tests/` |
| 前端 vitest 回归 | ✅ | `web/tests/` |
| 前端 `pnpm build` 生产构建验证 | ✅ | |
| OpenAPI 契约生成 | ✅ | `web/lib/api/generated/openapi.ts` 由 `web/scripts/` 代码自动生成 |

---

## 三、Roadmap

三个阶段，前两个阶段基本完成，第三阶段（"从单次调用到持续写作系统"）进入基础闭环。

### Phase 1：基础平台 + 风格实验室

| 项目 | 状态 |
| --- | --- |
| 基础框架（鉴权、Provider、项目 CRUD） | ✅ |
| Style Lab 深度分析结果包 | 🧪 |
| Plot Lab 基础闭环 | ✅ |
| Style Lab 多 TXT 合并 / 独立证据账本 / 超长文本批处理 / 采样聚合质量升级 / 外部任务队列 | ⏳ |

### Phase 2：Zen Editor

| 项目 | 状态 |
| --- | --- |
| 极简编辑器 | ✅ |
| 概念生成与灵感卡片（Concept Gacha） | ✅ |
| AI 续写与风格挂载 | ✅ |
| Ghost Text 自动续写 / 划词改写增强 | ⏳（划词改写有菜单版，但 Ghost Text 自动补全未开始）|

### Phase 3：Memory

| 项目 | 状态 |
| --- | --- |
| 蓝图 / 活态双层架构 | ✅ |
| 节拍驱动的结对写作（Beat-Driven） | ✅ |
| AI 自动提议活态层（`runtime_state` / `runtime_threads`） | ✅ |
| 自动拼装长期上下文 | ✅ |
| 从"单次调用"提升为"持续写作系统" | 🔁（已完成基础闭环）|

### Phase 4（潜在）：Style Generator 管道

当前未列入 Roadmap，但架构预留：

- Style Generator Graph：Context Builder Node → Draft Node → Critic Node
- Critic Node：高频词、忌讳词、句长分布、风格偏差校验
- 使用与 Style Analysis 同样的 LangGraph + checkpointer + worker 范式

---

## 四、当前真实水位线

用一句话总结：

> **Persona 已经完成了从基础平台 → 风格/情节分析资产生产 → 沉浸式创作与记忆同步的完整闭环**，成为一个真正可用的 AI 创作系统。  
> 大模型已从"黑盒生成器"被驯化为"受约束、有记忆的结对写作工具"。

下一步优化集中在：

1. **Style Lab 的多样本合并**、更稳定的长文本特征提取、独立证据账本持久化
2. **Ghost Text 自动补全续写** + 更流畅的划词改写（Inline Copilot）
3. **更轻量的上下文缓存策略**（探索 native Prompt Caching 与 KV Cache 复用）

---

## 五、如何确认某功能的当前状态

如果你拿到任务时不确定功能是否可用：

1. 先查本表——如果标记 ✅ 或 🧪，基本能用
2. 去对应的 Wiki 章节看实现细节（例如 "Style Lab" → `20-domains/26-style-lab.md`）
3. 跑一下相关测试（`api/tests/` 或 `web/tests/`），通过的测试代表当前实现保底
4. 启动 `make dev`，在浏览器里实际点一下——比读代码更快

---

## 下一篇

进入 [10 架构总图](../10-architecture/10-high-level-architecture.md)，从工程视角看系统怎么组装起来。
