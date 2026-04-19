# 90 术语表

| 术语 | 定义 |
| --- | --- |
| Persona | 一个单用户、BYOK、约束式的 AI 长篇创作平台。 |
| BYOK | Bring Your Own Key。用户自己提供模型 API Key。 |
| Project | 创作项目的根对象，承载 Provider、Style Profile、蓝图字段与运行时字段。 |
| Style Lab | 上传 TXT 样本、分析文风并生成风格资产的模块。 |
| Style Analysis Job | 一次后台风格分析任务，对应 `style_analysis_jobs` 记录。 |
| Style Profile | 可长期复用的风格档案，包含报告、摘要、Prompt Pack。 |
| Prompt Pack | 会被后续写作系统提示词直接注入的风格母 Prompt。 |
| Bible | 项目级创作资产面板，包含蓝图层与活态层。 |
| 蓝图层 | 作者长期维护的 `inspiration / world_building / characters / outline_*` 等字段。 |
| 活态层 | 随正文推进而变化的 `runtime_state / runtime_threads`。 |
| Runtime State | 会影响后续章节连续性的稳定事实、关系变化和新规则。 |
| Runtime Threads | 尚未回收的伏笔、风险、线索与设定约束备忘。 |
| Chapter Tree | `outline_detail` 的结构化投影层，对应 `project_chapters`。 |
| Zen Editor | Persona 的主写作界面，承载正文编辑、节拍写作、续写和记忆同步。 |
| Beat | 一个最小叙事单元，用一句话概括接下来要发生的事。 |
| SSE | Server-Sent Events。Persona 用它做流式文本生成。 |
| RSC | React Server Components。Next.js App Router 默认的组件执行形态。 |
| Server Action | 在 Next.js 服务端执行、可被客户端直接触发的轻量 RPC 风格函数。 |
| Checkpointer | LangGraph 的断点持久化层；Persona 可落到 Postgres 或 SQLite。 |
| Worker Lease | Worker 通过数据库字段 claim 任务并维持租约的机制。 |
| Markdown-First | 不强制模型输出 JSON，而是用 Markdown 结构做约束与持久化。 |
| Memory Sync | 把正文变化提炼成活态层更新提议的流程。 |
| Pending Review | 记忆同步已生成提议，但还没被作者接受。 |

## 相关章节

- [00 Persona 是什么](../00-overview/00-what-is-persona.md)
- [13 数据模型](../10-architecture/13-data-model.md)
- [22 Zen Editor](../20-domains/22-zen-editor.md)
- [26 Style Lab](../20-domains/26-style-lab.md)
- [27 Style Analysis 管道](../20-domains/27-style-analysis-pipeline.md)
