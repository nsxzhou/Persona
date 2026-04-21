# 91 常见问题与调试 FAQ

## Worker 一直不处理 Style Lab 任务，为什么？

先看 `make status` 是否显示 Worker 在跑，再看 `.run/worker.log`。常见原因：

- `PERSONA_STYLE_ANALYSIS_WORKER_ENABLED=false`
- Worker 根本没启动
- 任务被 pause 了
- 旧任务处于 `running` 但 lease 还没过期

相关代码：`api/app/worker.py:9`、`api/app/services/style_analysis_worker.py:427`。

## Style Lab 页面一直显示 pending，没有日志输出，正常吗？

不正常。日志增量接口走 `api/app/api/routes/style_analysis_jobs.py:123`，真正写日志的是 `api/app/services/style_analysis_storage.py:181`。如果状态变化了但没日志，优先查 Worker 执行是否在 `_load_run_context()` 前就失败了。

## Provider 测试连接报错，但我看不见完整原始错误，为什么？

这是有意设计。Persona 会对异常做脱敏和截断，避免把 token、Bearer 或 URL query 里的敏感字段直接回显到 UI。看实现：

- `api/app/core/redaction.py:25`
- `api/app/services/provider_configs.py:138`

## 记忆同步为什么经常提示“无更新”？

因为 Memory Sync 不是摘要器。它只记录“会影响后续章节的持续性变化”。如果本章只是情绪波动、一次性动作或没有新增长期约束，返回 `no_change` 是正确行为。Prompt 规则见 `api/app/services/editor_prompts.py:490`。

## 打开 Diff Dialog 后为什么还能手工改 AI 提议？

这是设计目标，不是调试开关。Persona 把运行时记忆更新视为“AI 提议 + 人工签字”，而不是自动落库。实现见 `web/components/bible-diff-dialog.tsx:189`。

## 为什么我改了 Prompt，结果接口还是按旧格式解析？

大概率只改了 Prompt，没同步改 parser 或 Schema。先检查：

- `api/app/schemas/editor.py`
- `api/app/services/editor_prompts.py`
- `api/app/schemas/style_analysis_jobs.py`
- `api/app/services/style_analysis_prompts.py`

规则出处：`AGENT.md:40`。

## 前端页面能跑，`pnpm build` 却失败，为什么？

因为 Persona 使用 Next.js App Router，很多 RSC / Client Component 边界问题只会在构建期暴露。`pnpm build` 不是可选项。脚本见 `web/package.json:7`。

## 导出文件缺少我刚写的最后几段，为什么？

导出读取的是数据库里的 `project_chapters`，不是浏览器 textarea 当前内存状态。先确认自动保存已经完成，或手动保存当前章。相关链路：

- `web/hooks/use-editor-autosave.ts:25`
- `api/app/api/routes/projects.py:139`

## 为什么删除 Provider / Style Profile 会报“正在被引用”？

这也是有意设计。删除会先检查是否仍被项目或 Style Lab 资产引用，防止把正在使用的配置删掉。相关代码：

- `api/app/services/provider_configs.py:156`
- `api/app/services/style_profiles.py:133`

## 相关章节

- [15 LLM Provider 接入](../10-architecture/15-llm-provider-integration.md)
- [16 SSE 与流式响应](../10-architecture/16-sse-and-streaming.md)
- [26 Style Lab](../20-domains/26-style-lab.md)
- [27 Style Analysis 管道](../20-domains/27-style-analysis-pipeline.md)
- [30 记忆同步](../20-domains/30-memory-sync.md)
- [51 测试策略](../50-standards/51-testing-strategy.md)
