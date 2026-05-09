# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

Persona uses async SQLAlchemy 2.0 with `asyncpg` for normal Postgres work and Alembic for migrations. Database access belongs in repositories and transaction policy belongs in the service/request or worker unit of work.

---

## Query Patterns

- Use SQLAlchemy 2.0 builders such as `select()` and `insert().returning()`.
- Do not use legacy `session.query()`.
- Use `selectinload` for one-to-many and many-to-many relationships.
- Use `joinedload` for many-to-one and one-to-one relationships.
- Prefer `raiseload("*")` in core query paths when accidental lazy loading would hide N+1 problems.
- For large reads, use streaming or batching such as `stream_scalars()` or `yield_per()`.
- For bulk changes, use `update().where(...)` / `update().values(...)` instead of row-by-row mutation loops.

## Transaction Management

- Normal HTTP requests should rely on `get_db_session` to commit on success and roll back on exceptions.
- Services should not call `commit()` in ordinary request paths; use `flush()` only when generated values are needed before return.
- Complex business operations and background workers should use explicit async unit-of-work boundaries such as `async with session.begin():`.
- Keep database sessions out of LangGraph state, Pydantic payloads, and other serializable workflow state.

---

## Migrations

- Schema changes must be represented in SQLAlchemy models and Alembic migrations.
- Review generated Alembic migrations before accepting them.
- Migration defaults must preserve behavior for existing rows.

## Scenario: Project prompt assets

### 1. Scope / Trigger
- Trigger: project-scoped prompt stack assets that affect runtime LLM context.
- This is a cross-layer contract: DB schema, project API, prompt stack selection, runtime workflow payloads, Prompt Trace, and frontend workbench state must stay aligned.

### 2. Signatures
- DB table: `project_prompt_assets`
  - `id STRING(36) PRIMARY KEY`
  - `project_id STRING(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE`
  - `chapter_id STRING(36) NULL REFERENCES project_chapters(id) ON DELETE CASCADE`
  - `kind STRING(32) NOT NULL`: `character_card | lorebook_entry | author_note`
  - `scope STRING(16) NOT NULL`: `project | chapter`
  - `title STRING(160) NOT NULL`
  - `content TEXT NOT NULL`
  - `keywords_payload JSON NOT NULL`
  - `enabled BOOLEAN NOT NULL DEFAULT true`
  - `always_on BOOLEAN NOT NULL DEFAULT false`
  - `priority INTEGER NOT NULL DEFAULT 0`
- API:
  - `GET /api/v1/projects/{project_id}/prompt-assets`
  - `POST /api/v1/projects/{project_id}/prompt-assets`
  - `PATCH /api/v1/projects/{project_id}/prompt-assets/{asset_id}`
  - `DELETE /api/v1/projects/{project_id}/prompt-assets/{asset_id}`
  - `POST /api/v1/projects/{project_id}/prompt-stack/preview`

### 3. Contracts
- Assets are owned through `project_id`; every read/write must first prove the current user owns the project.
- Chapter-scoped assets must bind to a `chapter_id` that belongs to the same project and user.
- Project-scoped assets must store `chapter_id = NULL`.
- `keywords_payload` is the storage field; API responses expose it as `keywords`.
- Prompt activation is deterministic:
  - skip disabled assets
  - select `always_on` assets
  - select assets whose keywords appear in activation text
  - sort by `priority DESC`, then stable title/id tie-breakers
- Prompt stack preview is a dry-run contract; it must not invoke an LLM.
- Runtime workflow payloads that target a selected chapter must include `chapter_id` so chapter-scoped assets can activate.

### 4. Validation & Error Matrix
- Unknown project or project owned by another user -> `404 项目不存在`.
- Asset id not in project -> `404 Prompt 资产不存在`.
- `scope = chapter` and missing `chapter_id` -> `422 章节级 Prompt 资产必须绑定章节`.
- `scope = project` with `chapter_id` -> `422 项目级 Prompt 资产不能绑定章节`.
- `chapter_id` not owned by project/user -> `404 章节不存在`.
- Disabled asset with matching keyword -> not selected.
- Enabled keyword asset with no match and `always_on = false` -> not selected.

### 5. Good/Base/Bad Cases
- Good: a chapter-scoped author note with keyword `雨夜` activates only for that chapter when current context contains `雨夜`.
- Base: a project-scoped lorebook entry with `always_on = true` activates for all writing calls in the project.
- Bad: frontend sends no `chapter_id` for beat expansion; trace shows a stack manifest but the intended chapter-scoped asset never activates.

### 6. Tests Required
- API CRUD tests for create/list/update/delete, ownership, and scope validation.
- Selection tests for disabled, always-on, keyword, priority, project scope, and chapter scope.
- Preview endpoint test proving no model call and verifying layer manifest fields.
- Runtime workflow tests proving selected asset text reaches continuation/beat expansion prompts.
- Trace tests proving stack manifest renders without breaking existing prompt trace output.
- Frontend contract tests for API client payloads, workbench tab rendering, and editor workflow `chapter_id` propagation.

### 7. Wrong vs Correct

#### Wrong
Store prompt stack assets as extra Markdown sections inside `ProjectBible.characters_blueprint` and infer activation from headings.

#### Correct
Store prompt stack assets in `project_prompt_assets`, validate scope at API/service boundaries, and pass a selected prompt stack layer into runtime context assembly.

## Scenario: Prompt asset initialization suggestions

### 1. Scope / Trigger
- Trigger: LLM-assisted initialization of prompt assets from an existing project.
- This is a cross-layer contract: Novel Workflow artifacts, project APIs, prompt asset service validation, OpenAPI-generated frontend types, and Prompt Stack tab state must stay aligned.

### 2. Signatures
- Workflow intent: `prompt_asset_init`.
- Workflow artifact: `prompt_asset_suggestions`.
- Apply API: `POST /api/v1/projects/{project_id}/prompt-assets/apply-suggestions`.
- Suggestion change shape:
  - `action`: `new | update | disable`
  - `asset_id`: required for `update` and `disable`, omitted for `new`
  - `rationale`: optional human-readable reason
  - `payload`: `ProjectPromptAssetBase` for `new` and `update`, omitted for `disable`

### 3. Contracts
- Generation is read-only: it may read project description, `ProjectBible`, and existing prompt assets, then write only the workflow artifact.
- Generation must not create, update, or disable `project_prompt_assets`.
- Confirmation is explicit: only the apply API mutates prompt assets.
- Apply must reuse `PromptStackService.create_asset()` and `PromptStackService.update_asset()` so existing ownership, scope, chapter, keyword normalization, and validation rules remain authoritative.
- Do not introduce a draft table or parallel asset store for M2 suggestions.
- The workflow must not read chapter content in the first version.

### 4. Validation & Error Matrix
- `new` without `payload` -> `422 新增 Prompt 资产建议缺少 payload`.
- `update` without `asset_id` -> `422 更新或禁用 Prompt 资产建议缺少 asset_id`.
- `update` without `payload` -> `422 更新 Prompt 资产建议缺少 payload`.
- `disable` without `asset_id` -> `422 更新或禁用 Prompt 资产建议缺少 asset_id`.
- `asset_id` outside the target project -> `404 Prompt 资产不存在`.
- Invalid payload scope/chapter rules -> same validation errors as normal prompt asset CRUD.

### 5. Good/Base/Bad Cases
- Good: `prompt_asset_init` returns a JSON artifact with one `new` character card and one `update` lorebook entry; no assets change until the user confirms.
- Base: empty or already complete projects may return `{"changes":[]}`.
- Bad: workflow generation silently creates disabled assets as drafts; this violates the explicit confirmation contract.

### 6. Tests Required
- Parser tests for fenced JSON suggestion output.
- Workflow test proving `prompt_asset_init` writes only `prompt_asset_suggestions` and does not return a project Bible writeback payload.
- Apply API tests for `new`, `update`, and `disable`.
- Project isolation tests proving an `asset_id` from another project is rejected.
- Frontend contract tests for workflow creation, artifact fetch, and apply endpoint payload.

### 7. Wrong vs Correct

#### Wrong
Persist LLM suggestions into a new draft table or immediately write them as disabled `project_prompt_assets`.

#### Correct
Persist suggestions only as a workflow artifact, render them in the Prompt Stack tab, and apply confirmed changes through the existing prompt asset service.

## Scenario: Provider immersion prompt override

### 1. Scope / Trigger
- Trigger: provider configuration changes that add runtime prompt behavior.
- This is a cross-layer contract: DB fields, Provider CRUD API, LLM message assembly, Prompt Trace, and frontend Provider settings must stay in sync.

### 2. Signatures
- DB table: `provider_configs`
  - `immersion_prompt_override_enabled BOOLEAN NOT NULL DEFAULT false`
  - `immersion_system_prompt_suffix TEXT NOT NULL DEFAULT ''`
- Backend schemas:
  - `ProviderConfigCreate`
  - `ProviderConfigUpdate`
  - `ProviderConfigResponse`
- Runtime entrypoint:
  - `LLMProviderService.invoke_completion(..., injection_mode="immersion" | "analysis" | "none", ...)`

### 3. Contracts
- The override is Provider-scoped, not project-scoped.
- The override applies only when all conditions are true:
  - resolved injection mode is `immersion`
  - `immersion_prompt_override_enabled` is true
  - `immersion_system_prompt_suffix.strip()` is non-empty
- When applied, append `immersion_system_prompt_suffix` to the final `SystemMessage.content`.
- Do not append the suffix to `HumanMessage.content`.
- Keep the existing first-human-message marker injection unchanged.
- Prompt Trace must show `Provider prompt override | yes/no`; the full suffix appears only inside the final System message.

### 4. Validation & Error Matrix
- Missing override fields on old rows -> migration defaults to disabled and empty suffix.
- Disabled override with non-empty suffix -> no runtime prompt change.
- Enabled override with blank suffix -> no runtime prompt change.
- `analysis` or `none` mode -> no runtime prompt change.
- Connection edit form submit -> must not include prompt override fields.
- Prompt override dialog submit -> must include only prompt override fields.

### 5. Good/Base/Bad Cases
- Good: local Provider enables immersion override; prose generation calls include the suffix in `SystemMessage`; analysis calls do not.
- Base: existing Provider rows continue with override disabled after migration.
- Bad: shared Provider connection form carries hidden prompt fields and overwrites prompt override settings during unrelated edits.

### 6. Tests Required
- Migration test: existing Provider rows get disabled/empty defaults.
- Provider CRUD test: create/update/response include the new fields.
- LLM unit test: immersion applies suffix; analysis/disabled/blank suffix does not; user marker remains.
- Prompt Trace test: yes/no metadata is rendered and final System message contains the suffix when applied.
- Frontend tests: prompt dialog saves override fields; connection edit does not submit override fields.

---

## Naming Conventions

- Keep ORM model fields, Pydantic schema fields, OpenAPI output, and frontend generated types aligned.
- When a storage field is intentionally exposed under a different API name, document the mapping in the relevant contract scenario.

---

## Common Mistakes

- Writing SQL directly in Routers instead of Repositories.
- Relying on lazy loading in async contexts.
- Calling `result.all()` on large result sets.
- Managing request commits manually inside service methods.
