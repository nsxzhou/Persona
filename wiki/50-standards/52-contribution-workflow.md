# 52 贡献与 Git 流程

## 要解决什么问题

Persona 目前没有复杂的发布流水线，但本地贡献仍然应该有一条稳定的收口路径，避免“代码改了、环境没跑、类型没核、文档没对齐”。

## 关键概念与约束

### 推荐的本地工作流

1. 先阅读相关实现与 `AGENT.md`
2. 跑 `make dev`，确认数据库 / API / Worker / Web 都正常
3. 做最小化修改
4. 跑相关验证
5. 再跑全量收口命令

对本仓库，最常用的收口组合是：

```bash
cd api && uv run pytest -q
cd web && pnpm test
cd web && pnpm build
```

这组命令来自根 README，见 `README.md:54`。

### 如果后端接口变了，别忘了 codegen

前端 OpenAPI codegen 脚本定义在 `web/package.json`：

- `pnpm run codegen:openapi:schema`
- `pnpm run codegen:openapi:types`
- `pnpm run codegen:style-lab`

当你改了后端 Schema 或路由响应时，应该先更新生成产物，再修前端引用，而不是手写类型临时兜底。

### Commit 与 PR 目前没有硬性机器人校验

仓库里当前没有独立的 commitlint 或 PR 模板约束，因此贡献流程以“清晰可审阅”为目标：

- 一个 commit 尽量聚焦一个主题
- 优先使用简洁前缀，例如 `feat:` / `fix:` / `docs:` / `refactor:` / `test:`
- PR 描述至少交代：改了什么、为什么改、怎么验证

这不是强制工具规则，但对多人协作和历史回溯非常重要。

## 实现位置与扩展点

### 一条推荐的提交前检查清单

- 本地环境能起来：`make dev`
- 相关测试已跑
- 前端 build 已过
- 如果动了接口，OpenAPI 产物已更新
- 如果动了 Prompt，相关 Schema / parser / 文档已同步

### 文档贡献也走同样的收口方式

如果你改的是 wiki：

- 抽样检查仓库路径、关键符号、路由名与少量保留行号
- 在 Markdown Preview 中看 Mermaid 是否可渲染
- 确认 `wiki/README.md` 导航没断

### GitHub 独立 Wiki 自动同步

仓库内 `wiki/` 目录是文档事实源。`.github/workflows/sync-github-wiki.yml` 会在 `main` 分支上有 `wiki/**` 变更时，自动把内容推到 `Persona.wiki.git`。

前提是仓库 secrets 中已配置：

- `WIKI_PUSH_TOKEN`：一个对 GitHub 独立 Wiki 仓库有写权限的 PAT

同步时还会把 `wiki/README.md` 复制成 GitHub Wiki 的 `Home.md`，保证独立 Wiki 首页和仓库内目录页保持一致。

## 常见坑 / 调试指南

| 症状 | 常见原因 | 建议 |
| --- | --- | --- |
| 后端改完，前端 types 还是旧的 | 忘了 codegen | 先跑 `pnpm run codegen:style-lab` |
| 本地功能看着能用，但 PR 后 build 爆 | 只跑了测试，没跑 `pnpm build` | 把 build 放进固定流程 |
| 改了 Prompt 却没同步 Schema | 只把它当文案改动 | 回看 [31 Prompt ↔ Schema 强绑定](../30-prompt-engineering/31-prompt-schema-coupling.md) |

## 相关章节

- [40 本地开发与 Makefile](../40-operations/40-local-dev-and-make.md)
- [51 测试策略](./51-testing-strategy.md)
- [31 Prompt ↔ Schema 强绑定](../30-prompt-engineering/31-prompt-schema-coupling.md)
- 根目录 `AGENT.md`
