# 16 SSE 与流式响应

## 要解决什么问题

Persona 的写作体验依赖“边生成边显示”，而不是等待整个 LLM 响应结束后一次性落地。流式层要解决：

- FastAPI 如何把 LLM chunk 按文本流推给浏览器
- 浏览器如何解析 `text/event-stream`
- 用户点击“停止”时如何取消正在进行的生成
- 编辑器续写、Bible 区块生成、分卷生成、章节细纲生成、逐拍展开如何共用一套流式基础设施

## 流式通道总图

```mermaid
flowchart LR
    UI[Client Component<br/>ZenEditor / OutlineDetail / BeatPanel]
    Hook[useStreamingText]
    Parser[consumeTextEventStream]
    Fetch[fetch Response.body]
    SSE[sse_response()]
    Editor[Editor routes]
    Service[EditorService / LLMProviderService]
    LLM[LLM Provider]

    UI --> Hook
    Hook --> Fetch
    Fetch --> Parser
    Parser --> Hook
    Fetch --> SSE
    SSE --> Editor
    Editor --> Service
    Service --> LLM
    LLM --> Service
    Service --> SSE
```

## 关键概念与约束

### 后端只做一件事：把字符串 chunk 包成标准 SSE frame

通用封装在 `api/app/api/sse.py:12`：

- 迭代 `AsyncGenerator[str, None]`
- 对每个 chunk 输出 `data: "<json-string>"\n\n`
- 出错时输出 `event: error\ndata: "<error>"\n\n`

这层非常薄，但价值很高：业务 Service 不需要知道 SSE 协议细节，只要“持续 yield 字符串”即可。

### 所有流式编辑器接口都挂在 `editor.py`

流式路由入口集中在 `api/app/api/routes/editor.py`：

- `/projects/{project_id}/editor/complete`，见 `api/app/api/routes/editor.py:50`
- `/projects/{project_id}/editor/generate-section`，见 `api/app/api/routes/editor.py:64`
- `/projects/{project_id}/editor/expand-beat`，见 `api/app/api/routes/editor.py:116`
- `/projects/{project_id}/editor/generate-volumes`，见 `api/app/api/routes/editor.py:130`
- `/projects/{project_id}/editor/generate-volume-chapters`，见 `api/app/api/routes/editor.py:143`

这些路由都遵循同一个模式：

1. 先向 Service 取回一个 async generator
2. 再统一交给 `sse_response()`

### Service 层的 generator 必须是“脱离 ORM 会话后的纯 Python 流”

`api/app/services/editor.py:1` 顶部注释写得很明确：

- 流式方法会在 DB session 仍然活着时，把 ORM 数据与 model 构造都准备好
- 然后只返回一个不再依赖 ORM 延迟加载的 async generator

这是为了避免 `StreamingResponse` 真正开始消费时，Session 已被依赖系统清理，从而触发 detached ORM 或 `MissingGreenlet` 问题。

### 前端先消费原始流，再节流刷新 React state

浏览器端分两层：

- `web/lib/sse.ts` 负责解析 `text/event-stream`，把 frame 还原成纯文本
- `web/hooks/use-streaming-text.ts` 负责管理 `ReadableStreamDefaultReader`、取消、以及 `requestAnimationFrame` 节流刷新

`useStreamingText()` 的关键行为在 `web/hooks/use-streaming-text.ts:36`：

- `consumeResponse()` 从 `response.body.getReader()` 取流
- 每收到 chunk 就更新 `fullText`
- 每 100ms 最多 flush 一次到 React state，避免过高频率重渲染
- `cancelStream()` 会直接 `reader.cancel()`，并把当前状态留在内存里

### 编辑器、章节细纲和逐拍展开共用同一套流式底座

代表性前端调用点：

- `web/hooks/use-editor-completion.ts` 调用 `/editor/complete`
- `web/components/workbench-tabs.tsx` 通过 `consumeTextEventStream()` 承载 Bible 区块生成
- `web/components/outline-detail-tab.tsx` 封装通用 `streamSSE()`，用于分卷与章节细纲生成
- `web/hooks/use-beat-generation.ts` 调用 `/editor/generate-beats` 与 `/editor/expand-beat`

这意味着 Persona 没有为每个 feature 各写一套“流式客户端协议”。统一协议带来三点好处：

- 错误处理一致
- 取消语义一致
- 新增一个流式生成能力时，只需要接到现有基础设施上

### 取消不是“回滚”，只是中断后续 chunk

取消逻辑在 `web/hooks/use-streaming-text.ts:26`：

- 取消时只会停止继续读流
- 已经 flush 到 UI 的文本会保留
- 调用方自己决定是否把已生成片段写入章节、是否触发记忆同步

例如编辑器续写在 `web/hooks/use-editor-completion.ts:76` 里只在 `currentGenerated.trim()` 非空时，才调用 `onGeneratedContent()` 做后续处理。

## 实现位置与扩展点

### 关键文件

| 文件 | 用途 |
| --- | --- |
| `api/app/api/sse.py` | 通用 SSE 包装器 |
| `api/app/api/routes/editor.py` | 所有流式编辑器端点 |
| `api/app/services/editor.py` | 生成 async generator 的真正业务层 |
| `api/app/services/llm_provider.py` | `astream()` / `stream_messages()` 的统一入口 |
| `web/lib/sse.ts` | 浏览器侧 SSE 协议解析 |
| `web/hooks/use-streaming-text.ts` | reader 管理、节流刷新、取消 |
| `web/hooks/use-editor-completion.ts` | 编辑器续写 |
| `web/hooks/use-beat-generation.ts` | 节拍展开 |
| `web/components/outline-detail-tab.tsx` | 分卷与章节细纲流式生成 |

### 扩展点

- 如果未来要加 Ghost Text 或实时补全，仍应复用 `useStreamingText()`，而不是再造一套 websocket 客户端
- 如果未来需要多种事件类型，可以在 `sse_response()` 上扩展 `event:` 语义，但文本主通道仍建议保持 `data` 为单一字符串
- 如果未来要加断线重连，应放在 `useStreamingText()` 层统一做，而不是每个业务 hook 单独重试

## 常见坑 / 调试指南

| 症状 | 常见原因 | 先看哪里 |
| --- | --- | --- |
| 浏览器能发请求但一直没有任何文本 | 后端 generator 没有真正 yield 字符串 | `api/app/services/editor.py` |
| 一取消就抛错误 toast | 没把 `"The operation was cancelled."` 识别为正常取消 | `web/hooks/use-streaming-text.ts:10` |
| 每个字都导致页面卡顿 | 没走 `requestAnimationFrame` 节流 | `web/hooks/use-streaming-text.ts:61` |
| 出错时 UI 无法显示后端错误详情 | 没处理 `event: error` frame | `web/lib/sse.ts:35` |
| 流式路由访问数据库时报 Session 失效 | generator 里仍在读 ORM 惰性属性 | `api/app/services/editor.py:1` |

## 相关章节

- [10 整体架构总图](./10-high-level-architecture.md) — SSE 在全局流程里的位置
- [12 前端架构](./12-frontend-architecture.md) — RSC / Client Component 与浏览器 fetch 的边界
- [15 LLM Provider 接入](./15-llm-provider-integration.md) — 流式调用最终如何落到 Provider
- [22 Zen Editor](../20-domains/22-zen-editor.md) — 编辑器续写与自动保存
- [24 大纲与节拍](../20-domains/24-outline-and-beats.md) — 分卷、分章和逐拍写作的流式场景
