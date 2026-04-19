# 51 测试策略

## 要解决什么问题

Persona 的验证不是“跑一条后端单测就算完”。这个仓库至少有三层需要分开理解：

- 后端 pytest：业务逻辑、API、数据库与部分 LLM 集成边界
- 前端 vitest：组件与交互逻辑
- 前端 build：RSC / 路由 / 类型边界的最终收口

## 关键概念与约束

### 后端：`pytest` 配置写在 `pyproject.toml`

这个仓库当前没有独立的 `pytest.ini`，而是把配置放在 `api/pyproject.toml:37`：

- `asyncio_mode = "strict"`
- `testpaths = ["tests"]`
- `pythonpath = ["."]`

最常用命令是：

```bash
cd api
uv run pytest -q
```

这也是根 README 给出的标准后端验证命令，见 `README.md:56`。

### 前端：Vitest 负责组件与 hook

前端脚本在 `web/package.json:5`：

- `pnpm test` -> `vitest run`
- `pnpm test:watch` -> 交互式模式

Vitest 配置在 `web/vitest.config.ts:4`：

- 运行环境是 `jsdom`
- 会加载 `vitest.setup.ts`
- 通过 `@` alias 指向仓库根下的 `web/`

因此前端单测更适合验证：

- 组件渲染与交互
- hooks 行为
- API 客户端与工具函数

### `pnpm build` 是前端最终收口

`web/package.json:7` 的 `build` 不能被 `vitest` 替代。它会额外暴露：

- RSC / Client Component 边界错误
- 未序列化 props
- Next.js 路由层问题
- 一些类型与构建期错误

对 Persona 这种 App Router 项目，`pnpm build` 是交付前必须看的最后一道门。

### LLM 相关测试分 mock 与 live 两层

`AGENT.md:104` 起已经把这件事讲清：

- 默认优先 mock，验证状态机和接口逻辑
- 只有在必须验证 Prompt 准确性或真实结构化输出边界时，才走 live provider
- live 凭证通过 `PERSONA_TEST_PROVIDER_*` 注入，见 `api/.env.example:65`

## 实现位置与扩展点

### 推荐验证顺序

1. 先跑与你改动直接相关的后端或前端测试
2. 再跑全量 `uv run pytest -q`
3. 再跑 `pnpm test`
4. 最后跑 `pnpm build`

### 什么时候要补测试

- 改 Service 逻辑：优先补后端 pytest
- 改组件交互或 hook：优先补 vitest
- 改 Prompt/Schema 契约：至少补 API / parser / 契约层验证
- 改路由边界或 RSC：必须看 `pnpm build`

## 常见坑 / 调试指南

| 症状 | 常见原因 | 建议 |
| --- | --- | --- |
| 后端单测都过了，前端页面还是挂 | 忘了跑 `pnpm build` | 把 build 当成必跑项 |
| 只跑了组件快照，业务回归还是漏掉 | 没验证 hook 或 API 契约 | 补更靠近业务链路的测试 |
| 本地 live provider 测试失败 | 环境变量没配或凭证过期 | 检查 `PERSONA_TEST_PROVIDER_*` |

## 相关章节

- [40 本地开发与 Makefile](../40-operations/40-local-dev-and-make.md) — 如何快速拉起环境后跑验证
- [50 编码规范](./50-coding-standards.md) — 测试要求的权威背景
- 根目录 `AGENT.md`
