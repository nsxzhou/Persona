# 13 数据模型与迁移

## 要解决什么问题

Persona 的业务逻辑全部建立在 **12 张核心表** 之上（其中 10 张是业务表，外加 `users` / `sessions` 两张基础表）。本章回答四个问题：

- 每张表有什么字段、用途、约束？表与表之间如何连通？
- 为什么所有业务资源都携带 `user_id`？
- 后端默认用 Postgres，但开发 / 测试可切 SQLite——迁移怎么做到两边都能跑？
- Alembic 的版本文件如何演进、新增字段 / 回滚怎么做？

读完本章，你应该能画出 ER 图凭记忆、能独立添加一张新表、能在遇到 "relation does not exist" 时准确定位到哪个 migration 没跑上。

## 关键概念与约束

### ER 图

```mermaid
erDiagram
    users ||--o{ sessions : "HttpOnly token"
    users ||--o{ provider_configs : "BYOK 凭证"
    users ||--o{ projects : "创作项目"
    users ||--o{ style_sample_files : "上传样本"
    users ||--o{ style_analysis_jobs : "分析任务"
    users ||--o{ style_profiles : "风格档案"
    users ||--o{ plot_sample_files : "上传情节样本"
    users ||--o{ plot_analysis_jobs : "情节分析任务"
    users ||--o{ plot_profiles : "情节档案"

    provider_configs ||--o{ projects : "default_provider"
    provider_configs ||--o{ style_analysis_jobs : "执行 provider"
    provider_configs ||--o{ style_profiles : "生成所用 provider"
    provider_configs ||--o{ plot_analysis_jobs : "执行 provider"
    provider_configs ||--o{ plot_profiles : "生成所用 provider"

    style_sample_files ||--|| style_analysis_jobs : "sample_file_id 1:1"
    style_analysis_jobs ||--o| style_profiles : "source_job_id 1:0..1"
    plot_sample_files ||--|| plot_analysis_jobs : "sample_file_id 1:1"
    plot_analysis_jobs ||--o| plot_profiles : "source_job_id 1:0..1"

    style_profiles ||--o{ projects : "挂载（可选）"
    plot_profiles ||--o{ projects : "挂载（可选）"

    projects ||--|| project_bibles : "Bible"
    projects ||--o{ project_chapters : "章节"

    users {
        string id PK
        string username UK
        string password_hash
        datetime created_at
        datetime updated_at
    }
    sessions {
        string id PK
        string user_id FK
        string token_hash UK
        datetime expires_at
        datetime last_accessed_at
    }
    provider_configs {
        string id PK
        string user_id FK
        string label
        string base_url
        text api_key_encrypted
        string api_key_hint_last4
        string default_model
        bool is_enabled
        string last_test_status
        text last_test_error
        datetime last_tested_at
    }
    projects {
        string id PK
        string user_id FK
        string name
        text description
        string status
        string default_provider_id FK
        string default_model
        string style_profile_id FK
        string plot_profile_id FK
        json generation_profile_payload
        string length_preset
        bool auto_sync_memory
        datetime archived_at
    }
    project_bibles {
        string id PK
        string project_id FK
        text inspiration
        text world_building
        text characters
        text outline_master
        text outline_detail
        text runtime_state
        text runtime_threads
    }
    project_chapters {
        string id PK
        string project_id FK
        int volume_index
        int chapter_index
        text title
        text content
        int word_count
        string memory_sync_status
        string memory_sync_source
        string memory_sync_scope
        datetime memory_sync_checked_at
        string memory_sync_checked_content_hash
        text memory_sync_error_message
        text memory_sync_proposed_state
        text memory_sync_proposed_threads
    }
    style_sample_files {
        string id PK
        string user_id FK
        string original_filename
        string content_type
        text storage_path
        int byte_size
        int character_count
        string checksum_sha256
    }
    style_analysis_jobs {
        string id PK
        string user_id FK
        string style_name
        string provider_id FK
        string model_name
        string sample_file_id FK
        string status
        string stage
        text error_message
        json analysis_meta_payload
        text analysis_report_payload
        text style_summary_payload
        text prompt_pack_payload
        string locked_by
        datetime locked_at
        datetime last_heartbeat_at
        datetime pause_requested_at
        datetime paused_at
        int attempt_count
        datetime started_at
        datetime completed_at
    }
    style_profiles {
        string id PK
        string user_id FK
        string source_job_id FK
        string provider_id FK
        string model_name
        string source_filename
        string style_name
        text analysis_report_payload
        text style_summary_payload
        text prompt_pack_payload
    }
    plot_sample_files {
        string id PK
        string user_id FK
        string original_filename
        string content_type
        text storage_path
        int byte_size
        int character_count
        string checksum_sha256
    }
    plot_analysis_jobs {
        string id PK
        string user_id FK
        string plot_name
        string provider_id FK
        string model_name
        string sample_file_id FK
        string status
        string stage
        text error_message
        json analysis_meta_payload
        text analysis_report_payload
        text plot_summary_payload
        text prompt_pack_payload
        text plot_skeleton_payload
        string locked_by
        datetime locked_at
        datetime last_heartbeat_at
        datetime pause_requested_at
        datetime paused_at
        int attempt_count
        datetime started_at
        datetime completed_at
    }
    plot_profiles {
        string id PK
        string user_id FK
        string source_job_id FK
        string provider_id FK
        string model_name
        string source_filename
        string plot_name
        text analysis_report_payload
        text plot_summary_payload
        text prompt_pack_payload
        text plot_skeleton_payload
    }
```

关键关系：

- **`users` 是一切的源头**：所有业务资源都带 `user_id` FK + `ondelete="CASCADE"`，删用户级联清账
- **`style_sample_files ↔ style_analysis_jobs` 是 1:1**：`StyleAnalysisJob.sample_file_id` 带 `unique=True`，一个样本最多绑一个任务
- **`style_analysis_jobs → style_profiles` 是 1:0..1**：`StyleProfile.source_job_id` 带 `unique=True`，任务跑完可选择保存成 profile；只有保存后才有对应的 profile 记录
- **`projects → style_profiles` 是 N:0..1**：项目可以挂载一个 Style Profile（也可以不挂）
- **`plot_sample_files ↔ plot_analysis_jobs` 是 1:1**：`PlotAnalysisJob.sample_file_id` 带 `unique=True`，一个样本最多绑一个任务
- **`plot_analysis_jobs → plot_profiles` 是 1:0..1**：`PlotProfile.source_job_id` 带 `unique=True`，成功任务可保存成长期情节档案
- **`projects → plot_profiles` 是 N:0..1**：项目可以挂载一个 Plot Profile（也可以不挂）

### 表结构逐项

所有模型定义在 `api/app/db/models.py`。基类 `Base` 是 SQLAlchemy 2.0 的 `DeclarativeBase`（`api/app/db/base.py`）。通用 `TimestampMixin`（`models.py:28-41`）为每张表加 `created_at` / `updated_at`，默认值用 `func.now()`（DB 生成）+ Python 端 `datetime.now(UTC)` 双保险。

所有主键 `id` 都是 **UUID v4 字符串**（`String(36)`，Python 端 `uuid.uuid4()`）——跨方言兼容、便于导出/导入、不暴露自增序号。

#### `users`（`models.py:44-69`）

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK, UUID | 用户 ID |
| `username` | String(64) | Unique, not null | 登录用户名（单用户部署下可随意） |
| `password_hash` | String(255) | not null | Argon2 哈希，非明文；见 `api/app/core/security.py` |
| `created_at` / `updated_at` | DateTime(tz) | not null | TimestampMixin |

Relationships：`sessions`, `provider_configs`, `projects`, `style_sample_files`, `style_analysis_jobs`, `style_profiles`, `plot_sample_files`, `plot_analysis_jobs`, `plot_profiles`，全部 `cascade="all, delete-orphan"`——删 user 一锅端。

#### `sessions`（`models.py:72-90`）

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK | Session ID（非 cookie 值） |
| `user_id` | String(36) | FK `users.id` ON DELETE CASCADE | 归属用户 |
| `token_hash` | String(128) | Unique, Index | HMAC 哈希（查询索引） |
| `expires_at` | DateTime(tz) | not null | 过期时间 |
| `last_accessed_at` | DateTime(tz) | not null | 最近访问（用于滑动过期） |

**不存 raw token**——cookie 里是 raw，DB 只存 HMAC，防止 DB 泄露即会话被盗。详见 [14 鉴权与 Session](./14-auth-and-session.md)。

#### `provider_configs`（`models.py:93-124`）

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK | Provider 配置 ID |
| `user_id` | String(36) | FK + Index | 所属用户 |
| `label` | String(100) | not null | 用户自命名（"OpenAI 官方" / "OpenRouter" 等） |
| `base_url` | String(255) | not null | OpenAI-compatible endpoint |
| `api_key_encrypted` | Text | not null | AES-GCM 密文（见 `api/app/services/provider_configs.py`） |
| `api_key_hint_last4` | String(4) | not null | 后四位明文，用于 UI 显示 `****xxxx` |
| `default_model` | String(100) | not null | 默认模型名（如 `gpt-4o-mini`） |
| `is_enabled` | Boolean | not null, default True | 逻辑禁用开关 |
| `last_test_status` | String(32) | nullable | 最近测试结果（`ok` / `failed`） |
| `last_test_error` | Text | nullable | 测试错误详情 |
| `last_tested_at` | DateTime(tz) | nullable | 测试时间 |

Relationship：`projects`, `style_analysis_jobs`, `style_profiles`, `plot_analysis_jobs`, `plot_profiles` 都引用它（作为 `default_provider` / `provider`）。`api_key_hint` 是 Python 属性（`f"****{last4}"`），不是列。

#### `projects`（`models.py:127-172`）

这是业务中心表，字段最多。按语义分组：

**元数据**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | String(36) | PK |
| `user_id` | String(36) | FK + Index |
| `name` | String(120) | 项目名（必填） |
| `description` | Text | 描述，默认空串 |
| `status` | String(16) | `draft` / `active` / `paused`，默认 `draft` |
| `archived_at` | DateTime(tz) | 归档时间戳（null 表示未归档） |

**外部依赖**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `default_provider_id` | String(36) | FK `provider_configs.id` + Index，必填 |
| `default_model` | String(100) | 项目级默认模型覆盖 |
| `style_profile_id` | String(36) | FK `style_profiles.id`，可选挂载 |
| `plot_profile_id` | String(36) | FK `plot_profiles.id`，可选挂载 |

**偏好**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `generation_profile_payload` | JSON | 独立保存的项目生成配置覆盖，支持定制化生成参数（可选） |
| `length_preset` | String(16) | `short` / `medium` / `long`，生成长度偏好 |
| `auto_sync_memory` | Boolean | 逐拍写作完成时是否静默自动同步记忆（默认 false） |

#### `project_bibles`

Bible 字段不再直接挂在 `Project` 上，而是拆成 1:1 的 `ProjectBible` 独立表。

**蓝图层**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `inspiration` | Text | 灵感笔记 / 项目起盘说明 |
| `world_building` | Text | 世界观设定 |
| `characters` | Text | 角色档案 |
| `outline_master` | Text | 总纲 / 分卷结构 |
| `outline_detail` | Text | 分章详细大纲 |

**活态层**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `runtime_state` | Text | 当前稳定生效的运行时状态 |
| `runtime_threads` | Text | 当前仍需追踪的线索、伏笔与约束 |

#### `project_chapters`（`models.py:174-207`）

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK | 章节 ID |
| `project_id` | String(36) | FK CASCADE + Index | 所属项目 |
| `volume_index` | Integer | not null | 分卷序号 |
| `chapter_index` | Integer | not null | 章序号 |
| `title` | Text | default "" | 章节标题 |
| `content` | Text | default "" | 正文 |
| `word_count` | Integer | default 0 | 字数缓存 |
| `memory_sync_status` | String(32) | nullable | `checking` / `pending_review` / `synced` / `no_change` / `failed` |
| `memory_sync_source` | String(32) | nullable | `auto` / `manual` |
| `memory_sync_scope` | String(32) | nullable | `generated_fragment` / `chapter_full` |
| `memory_sync_checked_at` | DateTime(tz) | nullable | 最近校验时间 |
| `memory_sync_checked_content_hash` | String(64) | nullable | 校验时的 content 哈希（变了需重检） |
| `memory_sync_error_message` | Text | nullable | 同步错误 |
| `memory_sync_proposed_state` | Text | nullable | AI 提议的新 `runtime_state` |
| `memory_sync_proposed_threads` | Text | nullable | AI 提议的新 `runtime_threads` |

**表级约束**：
```python
UniqueConstraint("project_id", "volume_index", "chapter_index",
                 name="uq_project_chapter_position")
```
保证同一项目内 (卷, 章) 组合唯一——防止重复插入。

#### `style_sample_files`（`models.py:210-225`）

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK | 样本 ID |
| `user_id` | String(36) | FK CASCADE + Index | 所属用户 |
| `original_filename` | String(255) | not null | 上传时文件名 |
| `content_type` | String(100) | nullable | MIME 类型 |
| `storage_path` | Text | not null | 本机绝对/相对路径（`PERSONA_STORAGE_DIR/...`） |
| `byte_size` | Integer | not null | 文件字节数 |
| `character_count` | Integer | nullable | 字符数（流式读取时填入） |
| `checksum_sha256` | String(64) | not null | SHA256 校验 |

**注意**：原始 TXT 内容**不入库**，只存 `storage_path` 指到本机文件——样本几百 KB 到几 MB，入库既浪费空间又难做增量。

#### `style_analysis_jobs`（`models.py:228-309`）

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK | 任务 ID |
| `user_id` | String(36) | FK CASCADE + Index | 所属用户 |
| `style_name` | String(120) | not null | 用户命名 |
| `provider_id` | String(36) | FK `provider_configs.id` | 使用的 Provider |
| `model_name` | String(100) | not null | 模型名 |
| `sample_file_id` | String(36) | FK CASCADE + Unique | 绑定的样本（1:1） |
| `status` | String(16) | not null, Index, default `pending` | `pending` / `running` / `paused` / `succeeded` / `failed` |
| `stage` | String(32) | nullable | 当前阶段（`preparing_input` / `analyzing_chunks` / `aggregating` / `reporting` / `postprocessing`） |
| `error_message` | Text | nullable | 失败原因 |
| `analysis_meta_payload` | **JSON** | nullable | 分析元数据（分块数、字符数、分类等） |
| `analysis_report_payload` | Text | nullable | 分析报告 Markdown |
| `style_summary_payload` | Text | nullable | Voice Profile Markdown |
| `prompt_pack_payload` | Text | nullable | Voice Profile Markdown |
| `locked_by` | String(64) | nullable | 当前持有者 Worker ID |
| `locked_at` | DateTime(tz) | nullable | 锁获取时间 |
| `last_heartbeat_at` | DateTime(tz) | nullable | 最近心跳 |
| `pause_requested_at` | DateTime(tz) | nullable | 用户请求暂停的时间 |
| `paused_at` | DateTime(tz) | nullable | 实际暂停生效时间 |
| `attempt_count` | Integer | not null, default 0 | 重试次数 |
| `started_at` | DateTime(tz) | nullable | 首次进入 `running` |
| `completed_at` | DateTime(tz) | nullable | 首次进入 `succeeded` |

**索引**（表级定义在 `models.py:231-247`）：

- `ix_style_analysis_jobs_status_created_at`：Worker claim 扫描用
- `ix_style_analysis_jobs_status_attempt_count_created_at`：重试计数策略用
- `ix_style_analysis_jobs_status_last_heartbeat_at`：卡死检测（`fail_stale_running_jobs`）用

这张表是 Persona 的"队列"：用 `status + locked_by + locked_at + last_heartbeat_at` 四字段做 "pending / claimed / running / stale" 状态机，不依赖 Redis 或外部队列。详见 [27 Style Analysis 管道](../20-domains/27-style-analysis-pipeline.md)。

**注意**：三大 Markdown 产物（`analysis_report_payload` / `style_summary_payload` / `prompt_pack_payload`）存在任务表，成功后会复制一份到 `style_profiles`。设计原因：**任务 = 时间切片**，可重跑；**profile = 长期资产**，挂载到项目使用。

#### `style_profiles`（`models.py:312-337`）

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK | 档案 ID |
| `user_id` | String(36) | FK CASCADE + Index | 所属用户 |
| `source_job_id` | String(36) | FK + Unique | 来源任务（1:1） |
| `provider_id` | String(36) | FK + Index | 生成所用 Provider |
| `model_name` | String(100) | not null | 模型名 |
| `source_filename` | String(255) | not null | 样本文件名（快照） |
| `style_name` | String(120) | not null | 用户命名 |
| `analysis_report_payload` | Text | not null | 分析报告（快照） |
| `style_summary_payload` | Text | not null | 摘要（可编辑） |
| `prompt_pack_payload` | Text | not null | Voice Profile（可编辑） |

挂载后，`Project.style_profile_id` 指向它；Editor 续写时自动注入 `prompt_pack_payload`。

#### `plot_sample_files`

结构与 `style_sample_files` 基本对称，只是服务于 Plot Lab：

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK | 样本 ID |
| `user_id` | String(36) | FK CASCADE + Index | 所属用户 |
| `original_filename` | String(255) | not null | 上传时文件名 |
| `content_type` | String(100) | nullable | MIME 类型 |
| `storage_path` | Text | not null | 本机绝对/相对路径（`PERSONA_STORAGE_DIR/...`） |
| `byte_size` | Integer | not null | 文件字节数 |
| `character_count` | Integer | nullable | 字符数 |
| `checksum_sha256` | String(64) | not null | SHA256 校验 |

和 Style Lab 一样，原始 TXT 不入库，只存本地文件路径与元数据。

#### `plot_analysis_jobs`

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK | 任务 ID |
| `user_id` | String(36) | FK CASCADE + Index | 所属用户 |
| `plot_name` | String(120) | not null | 用户命名 |
| `provider_id` | String(36) | FK `provider_configs.id` | 使用的 Provider |
| `model_name` | String(100) | not null | 模型名 |
| `sample_file_id` | String(36) | FK CASCADE + Unique | 绑定的样本（1:1） |
| `status` | String(16) | not null, Index, default `pending` | `pending` / `running` / `paused` / `succeeded` / `failed` |
| `stage` | String(32) | nullable | 当前阶段（`preparing_input` / `building_skeleton` / `selecting_focus_chunks` / `analyzing_focus_chunks` / `aggregating` / `reporting` / `postprocessing`） |
| `error_message` | Text | nullable | 失败原因 |
| `analysis_meta_payload` | **JSON** | nullable | 分析元数据（分块数、字符数、分类等） |
| `analysis_report_payload` | Text | nullable | 情节分析报告 Markdown |
| `plot_summary_payload` | Text | nullable | Story Engine Markdown |
| `prompt_pack_payload` | Text | nullable | Story Engine Markdown |
| `plot_skeleton_payload` | Text | nullable | 全书骨架 Markdown |
| `locked_by` | String(64) | nullable | 当前持有者 Worker ID |
| `locked_at` | DateTime(tz) | nullable | 锁获取时间 |
| `last_heartbeat_at` | DateTime(tz) | nullable | 最近心跳 |
| `pause_requested_at` | DateTime(tz) | nullable | 用户请求暂停的时间 |
| `paused_at` | DateTime(tz) | nullable | 实际暂停生效时间 |
| `attempt_count` | Integer | not null, default 0 | 重试次数 |
| `started_at` | DateTime(tz) | nullable | 首次进入 `running` |
| `completed_at` | DateTime(tz) | nullable | 首次进入 `succeeded` |

**索引**（表级定义在 `models.py` 的 `PlotAnalysisJob.__table_args__`）：

- `ix_plot_analysis_jobs_status_created_at`：Worker claim 扫描用
- `ix_plot_analysis_jobs_status_attempt_count_created_at`：重试计数策略用
- `ix_plot_analysis_jobs_status_last_heartbeat_at`：卡死检测（`fail_stale_running_jobs`）用

这张表与 `style_analysis_jobs` 一样承担“数据库内任务队列”的职责，但多了一份 `plot_skeleton_payload`，用于把全书骨架沉淀到任务结果和后续 profile 中。

#### `plot_profiles`

| 字段 | 类型 | 约束 | 用途 |
| --- | --- | --- | --- |
| `id` | String(36) | PK | 档案 ID |
| `user_id` | String(36) | FK CASCADE + Index | 所属用户 |
| `source_job_id` | String(36) | FK + Unique | 来源任务（1:1） |
| `provider_id` | String(36) | FK + Index | 生成所用 Provider |
| `model_name` | String(100) | not null | 模型名 |
| `source_filename` | String(255) | not null | 样本文件名（快照） |
| `plot_name` | String(120) | not null | 用户命名 |
| `analysis_report_payload` | Text | not null | 情节分析报告（快照） |
| `plot_summary_payload` | Text | not null | Story Engine（可编辑） |
| `prompt_pack_payload` | Text | not null | Story Engine（可编辑） |
| `plot_skeleton_payload` | Text | nullable | 全书骨架（可编辑或留空） |

挂载后，`Project.plot_profile_id` 指向它；规划和写作链路都会把其中的 Story Engine 作为约束输入。

### 横切约束：`user_id` scope

每张业务表（非 `users` / `sessions` 自身）都满足两条：

1. **有 `user_id` 字段**，FK 指向 `users.id`，带 `ondelete="CASCADE"` 与 `index=True`
2. **删除用户 = 清空所有业务数据**：User 侧 `cascade="all, delete-orphan"` 管关联记录；级联删除一步到位

这让 Persona 天然支持"单机多用户"形态（即便 MVP 只有一个管理员）：

- Repository 层查询统一 `.where(Model.user_id == user_id)`（详见 [11 后端分层](./11-backend-layering.md)）
- 任何"跨用户访问"的请求都因 WHERE 条件返回 None → Service 抛 `NotFoundError` → Router 返回 404
- 未来要加"管理员跨用户操作"只需在 Service 层加权限判断，数据结构已预备好

### Postgres + SQLite 双方言兼容

Persona 部署默认 Postgres 17（见根目录 `docker-compose.yml`），但开发 / 测试常用 SQLite in-memory。Alembic 迁移必须**两边都能跑**。

#### 设计约束

1. **列类型选最小公约数**：`String`, `Text`, `Integer`, `Boolean`, `DateTime(timezone=True)`, `JSON`。避免 Postgres-only 类型（`JSONB`, `ARRAY`, `UUID`, `INTERVAL`）
2. **不依赖 schema**：SQLite 无 schema 概念，所有表都在默认 schema
3. **`DateTime(timezone=True)` 在 SQLite 下会退化为 TEXT**（存 ISO8601 + tz），但行为仍一致
4. **`JSON` 列在 SQLite 下是 TEXT + 应用层序列化**，语义相同
5. **外键约束**：SQLite 默认关闭外键，但 `asyncpg` / `aiosqlite` 会在连接层开启——迁移里的 `ondelete="CASCADE"` 两边都生效
6. **主键字符串 UUID**：避免 Postgres 的 `UUID` 类型依赖，直接用 `String(36)`

#### URL 自动切换

`api/alembic/env.py:92-99` 对 URL 做一次"轻量自动补全"以兼容同步写法：

```python
if url.startswith("sqlite:///") and "+aiosqlite" not in url:
    url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
if (url.startswith("postgresql://") or url.startswith("postgres://")) and "+asyncpg" not in url:
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)\
             .replace("postgres://", "postgresql+asyncpg://", 1)
```

因此 `.env` 里写 `postgresql://user:pass@host/db` 或 `sqlite:///./persona.db` 都能被 Alembic 正确识别。

### 异步 Session + asyncpg / aiosqlite

`api/app/db/session.py:14-20`：

```python
def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, future=True)

def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
```

- **`create_async_engine`**：从 URL 自动挑 driver（`postgresql+asyncpg` / `sqlite+aiosqlite`）
- **`expire_on_commit=False`**：关键。commit 后 ORM 对象属性仍可用（SQLAlchemy 默认会失效，导致属性重查时 greenlet 崩）
- **`async_sessionmaker`**：SQLAlchemy 2.0 的异步会话工厂

Alembic 在运行时用 `NullPool`（`api/alembic/env.py:102`）：

```python
connectable = create_async_engine(url, poolclass=pool.NullPool)
async with connectable.connect() as connection:
    await connection.run_sync(do_run_migrations)
```

`NullPool` 不复用连接——迁移是一次性短任务，避免和应用并存时抢连接池。

### JSON 字段 vs Text 字段的取舍

Persona 里的"长文本"大多是 Markdown（`analysis_report_payload` / `prompt_pack_payload` / `characters` / `outline_master` 等），全部用 **Text**，不用 JSON。

**判别原则**：

| 用 Text | 用 JSON |
| --- | --- |
| 人类可读、可编辑 | 结构化、程序只按字段读 |
| 需要全文检索（未来） | 不需要 grep |
| 增量 diff 有语义（Markdown 行级） | 整块替换 |
| Prompt 模板直接注入 | 需要子字段独立查询 |

当前主要的 JSON 列是 `style_analysis_jobs.analysis_meta_payload` 与 `plot_analysis_jobs.analysis_meta_payload`——都属于**分析元数据**（分块数、字符数、输入分类字典），程序读为主，没有人工编辑需求。

**反模式**：用 Text 存 JSON 串再 `json.loads(...)`——Pydantic V2 + 原生 JSON 列能在 DB 层保持结构化，应用层直接拿 dict。

### Alembic 版本目录

`api/alembic/versions/` 目录列表：

```
0001_initial.py
0002_style_lab.py
0003_deep_analysis_results.py
0004_style_profiles_payload_only.py
0005_remove_style_job_draft_payload.py
0006_style_job_leases.py
0007_style_analysis_job_indexes.py
0008_sa_job_hot_path_idx.py
0009_user_scoped_resources.py
0010_markdown_style_lab_payloads.py
0011_style_job_pause.py
0012_plot_lab.py
0013_plot_skeleton_payload.py
0014_analysis_stage_renames.py
0015_gen_profile_payload.py
0ed5f4b2b7d7_add_project_content.py
915382ca98f5_add_project_content.py
a1b2c3d4e5f6_add_story_bible_fields.py
a418ffd86abe_add_length_preset_to_projects.py
b1c2d3e4f5a6_split_story_bible_to_runtime.py
c1d2e3f4a5b6_project_chapters.py
d3e4f5a6b7c8_chapter_memory_sync_fields.py
e4f5a6b7c8d9_add_auto_sync_memory_to_projects.py
```

#### 命名模式

两种风格混用：

1. **`NNNN_slug.py`**（`0001_initial.py` ~ `0015_gen_profile_payload.py`）：四位数字序号 + slug
   - 优点：文件字典序即升级顺序，直观
   - 缺点：不同 feature 分支并行开发时容易撞号
2. **`<hash>_slug.py`**（`a1b2c3d4e5f6_...`、`c1d2e3f4a5b6_...`）：Alembic `revision --autogenerate` 默认风格
   - 优点：无需协调数字序号
   - 缺点：字典序不一定等于升级顺序（靠 `down_revision` 链接）

**约定**：新增迁移直接用 `uv run alembic revision --autogenerate -m "..."`，让 Alembic 自动生成 hash；数字序号留给历史。**真正的顺序由每个文件内部的 `revision` / `down_revision` 决定**，不是文件名。

#### 迁移骨架

标准 Alembic 迁移文件结构：

```python
"""add foo to projects

Revision ID: <hash>
Revises: <prev_hash>
Create Date: 2024-12-01 12:34:56.789012
"""
from alembic import op
import sqlalchemy as sa

revision = "<hash>"
down_revision = "<prev_hash>"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("projects", sa.Column("foo", sa.Text(), nullable=False, server_default=""))

def downgrade() -> None:
    op.drop_column("projects", "foo")
```

### 迁移约定

#### 新增表

```bash
cd api
uv run alembic revision --autogenerate -m "add tags"
```

Alembic 会对照 `Base.metadata` 与当前数据库差异生成 `upgrade()` / `downgrade()`。**必须人肉 review**：

- 新列加默认值（`server_default=...`）——否则老行 NOT NULL 列插入失败
- 外键 `ondelete="CASCADE"` 是否该有
- 索引是否遗漏（`index=True` 的列 Alembic 会加，但 `__table_args__` 的联合索引需要手写）
- 跨方言的 `server_default` 写法：布尔默认用 `sa.false()` / `sa.true()`（见 `models.py:158`），不要写 `"false"` 字符串

#### 加字段

同上，只是 `op.add_column(...)`。**关键**：

- 在生产（已有数据）加 NOT NULL 列**必须**带 `server_default` 或先加 nullable、回填数据、再改 NOT NULL
- 加 FK 列要在同一迁移里创建外键约束（Alembic autogen 一般能搞定）

#### 回滚

```bash
uv run alembic downgrade -1       # 回退一步
uv run alembic downgrade <hash>   # 回退到某个 revision
uv run alembic downgrade base     # 回退到初始
```

**注意**：`downgrade()` 函数的质量取决于写的人——autogen 通常能反向推断，但涉及数据迁移的步骤需要手写反向脚本。一旦生产跑了迁移、破坏性改过数据，**回滚可能不可逆**。谨慎。

#### 查看当前版本 / 历史

```bash
uv run alembic current      # 当前数据库头部 revision
uv run alembic history      # 所有 revision 链
uv run alembic heads        # 查看分支（健康代码库只应一个 head）
```

多 head 意味着两个并行分支 revision 冲突，需要 `alembic merge` 生成合并 revision。

## 实现位置与扩展点

### 关键文件

| 文件 | 用途 |
| --- | --- |
| `api/app/db/base.py` | `Base = DeclarativeBase` 基类 |
| `api/app/db/models.py` | 所有 ORM 模型（UUID 主键 / TimestampMixin / 关系） |
| `api/app/db/session.py` | `create_engine` / `create_session_factory` / `get_db_session` |
| `api/alembic.ini` | Alembic 配置（`script_location = alembic`） |
| `api/alembic/env.py` | 异步迁移引擎（async + URL 自动补全 + NullPool） |
| `api/alembic/versions/` | 所有迁移文件 |
| `api/app/core/config.py` | `Settings.database_url`（优先级：`.env` > 默认 SQLite） |

### 新增一张表的完整流程

1. **定义 Model**：在 `api/app/db/models.py` 新增模型，沿用 UUID 主键、`TimestampMixin`、`user_id` scope 和关系声明风格
2. **补关系**：如有需要，在关联模型上补 `relationship(..., back_populates=...)`
3. **生成迁移**
   ```bash
   cd api
   uv run alembic revision --autogenerate -m "add <table>"
   ```
4. **Review 迁移文件**：检查外键、索引、默认值与跨方言兼容
5. **跑迁移**
   ```bash
   uv run alembic upgrade head
   ```
6. **后续层**：Schema / Repository / Service / Router（见 [11 后端分层](./11-backend-layering.md)）

### 扩展点

- **新增只读字段（如缓存/统计）**：`mapped_column(..., nullable=True)` + 迁移加列 + 业务代码在写入时计算
- **增加联合索引**：在 Model 的 `__table_args__` 加 `Index(...)` + 写迁移 `op.create_index(...)`（autogen 不会自动加联合索引）
- **表结构大改（拆字段 / 合并列）**：先加新列（迁移 1）→ 写数据回填（迁移 2，内嵌数据搬运）→ 删旧列（迁移 3）。**不要**一步到位。
- **加 Postgres-only 能力（JSONB 索引、`gin`）**：绕过 SQLite 兼容约束，需要在迁移里显式判断方言：`if op.get_bind().dialect.name == "postgresql": op.execute("CREATE INDEX ... USING gin(...)")`

## 常见坑 / 调试指南

### 迁移相关

| 症状 | 原因 | 修复 |
| --- | --- | --- |
| `relation "xxx" does not exist` | 迁移没跑到头 | `uv run alembic upgrade head` |
| `Target database is not up to date` | 有本地未提交的迁移 | `alembic stamp head` 强制对齐（慎用，只在明确知道状态时） |
| `Multiple heads are present` | 两条分支各自加了迁移 | `alembic merge <head1> <head2> -m "merge"` 生成合并 revision |
| `sqlalchemy.exc.OperationalError: no such column` | 模型加了新列但没加迁移 / 没跑迁移 | 生成并跑迁移 |
| autogen 漏检索引 | Alembic 对 `__table_args__` 里的 `Index` 检测不完整 | 手动在迁移里 `op.create_index(...)` |
| SQLite 下外键不生效 | SQLite 默认关 FK 约束 | 代码里已通过 driver 开启；如果手动连 SQLite 需 `PRAGMA foreign_keys = ON` |
| Postgres 下 `TIMESTAMP WITHOUT TIME ZONE` | `DateTime(timezone=True)` 写错成 `DateTime()` | 改 model 加 `timezone=True`，生成迁移 |

### 数据模型设计相关

| 症状 | 原因 | 修复 |
| --- | --- | --- |
| 删 user 后关联数据仍在 | 缺 `ondelete="CASCADE"` 或 Python 侧缺 `cascade="all, delete-orphan"` | 两处都加 |
| Repository 拿到 ORM 对象但属性访问 `greenlet_spawn has not been called` | 懒加载在异步上下文出错 | 在查询 options 预加载（`joinedload` / `selectinload`，详见 [11 后端分层](./11-backend-layering.md)） |
| `commit()` 后对象属性消失 | SQLAlchemy 默认 expire | 本项目已 `expire_on_commit=False`（`db/session.py:20`） |
| UUID 主键重复（极小概率） | `uuid4()` 碰撞 | 依赖数据库 Unique 约束，业务层捕获 IntegrityError 重试 |

### 开发切 SQLite

- `.env` 写 `PERSONA_DATABASE_URL=sqlite+aiosqlite:///./persona.db`
- **不要**用 SQLite in-memory 跑 alembic（alembic 会在一个新 engine 里执行，in-memory 内容拿不到）——文件 SQLite 才行
- 如果把 `PERSONA_DATABASE_URL` 指到 `sqlite+aiosqlite:///./persona.db`，这个本地 SQLite 文件会被 `.gitignore` 忽略

## 相关文件索引

- `api/app/db/base.py` — `Base = DeclarativeBase`
- `api/app/db/models.py` — 所有 ORM 模型（340+ 行）
- `api/app/db/session.py` — 异步 Session 工厂
- `api/alembic/env.py` — 迁移引擎（异步 + 双方言 URL 补全）
- `api/alembic.ini` — Alembic 主配置
- `api/alembic/versions/` — 迁移版本目录
- `api/app/core/config.py` — `Settings.database_url`
- `docker-compose.yml` — Postgres 17 容器
- `api/app/core/security.py` — 密码 Argon2 / 加密密钥逻辑（供 provider_configs 使用）
- `AGENT.md` §2.3 — 数据库操作规范出处

## 相关章节

- [10 整体架构总图](./10-high-level-architecture.md) — 数据库在系统里的位置
- [11 后端分层](./11-backend-layering.md) — Repository 层如何消费这些表
- [14 鉴权与 Session](./14-auth-and-session.md) — `users` / `sessions` 的使用细节
- [15 LLM Provider 接入](./15-llm-provider-integration.md) — `provider_configs` 的使用
- [20 项目](../20-domains/20-projects.md) — `projects` 纵切
- [21 章节树](../20-domains/21-chapter-tree.md) — `project_chapters` 纵切
- [26 Style Lab](../20-domains/26-style-lab.md) — `style_sample_files` / `style_analysis_jobs` / `style_profiles` 纵切
- [27 Style Analysis 管道](../20-domains/27-style-analysis-pipeline.md) — Worker 如何操作任务表做"队列"
- [41 数据库与 Alembic 迁移](../40-operations/41-database-and-migrations.md) — 运维视角的迁移操作
