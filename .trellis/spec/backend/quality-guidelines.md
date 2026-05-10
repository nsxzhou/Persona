# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

Backend changes must preserve Python 3.11+ typing, FastAPI dependency clarity, Pydantic V2 contracts, LLM prompt/schema coupling, memory safety, and deterministic tests.

---

## Forbidden Patterns

- Pydantic V1 APIs such as `parse_obj` and `dict()` for schema conversion; use `model_validate` and `model_dump`.
- Missing function parameter or return types.
- Repeatedly instantiating LLM clients inside chunk loops or graph nodes.
- Storing database sessions, network connections, or other unserializable objects in workflow state.
- Mutating global state or another node's state implicitly from a LangGraph node.
- Reading entire large uploads with `.read()` or loading unbounded database results with `result.all()`.
- Hard-coding API keys or live provider credentials in tests.
- Hard-coding large long-text samples directly in Python tests.

---

## Required Patterns

### Typing and Validation

- Use Python 3.11+ type hints such as `list[str]`, `dict[str, Any]`, and `str | None`.
- All request and response bodies must use Pydantic schemas.
- Use `Field` for explicit bounds, defaults, and validation metadata.
- FastAPI dependency injection should use `Annotated` aliases.

### LLM Workflows and State Machines

- Build and inject reusable LLM client instances during pipeline or graph initialization.
- Keep state objects as pure serializable data.
- Node business logic should be pure or update state through explicit return values.
- Prompt output format text must match the Pydantic schema or parser contract exactly.

## Scenario: Novel Workflow Full-Chapter Beat Expansion

### 1. Scope / Trigger
- Trigger: adding or changing a Novel Workflow prose-generation intent that crosses `NovelWorkflowCreateRequest`, workflow state, prompt builders, stored artifacts, OpenAPI output, and frontend editor hooks.

### 2. Signatures
- Backend request intent: `intent_type="chapter_expand"`.
- Request payload field: `beats: list[str] = Field(default_factory=list)`.
- Frontend client entry: `runChapterExpandWorkflow(projectId, chapterId, textBeforeCursor, runtimeState, runtimeThreads, outlineDetail, beats, currentChapterContext?, previousChapterContext?, styleProfileId?, plotProfileId?, options?)`.

### 3. Contracts
- `chapter_expand` must consume the full ordered beat list and write the generated chapter to artifact `prose_markdown`.
- It must also write the raw review result to artifact `chapter_expand_review`.
- Review issues are delivered through workflow `warnings` and frontend `reviewIssues`; clean reviews must produce no warning noise.
- The full-chapter writer is a prose surface, so it may inject both Voice Profile and Plot Writing Guide. Beat planning remains a planning surface and must not inject Voice Profile.
- Workflow payload `style_profile_id` / `plot_profile_id` must override the project defaults for that run; if omitted, use the project's mounted profiles.
- Runtime Prompt Stack activation must include the complete `beats` list so beat-keyword assets can activate for `chapter_expand`.

### 4. Validation & Error Matrix
- Empty `beats` in request -> backend may fall back to stored `beats_markdown` when available.
- Writer LLM failure -> workflow fails normally; no partial prose should be marked succeeded.
- Review LLM failure -> workflow must still succeed, preserve `prose_markdown`, and emit a review-warning message.
- Review output that is not parseable JSON -> treat the raw non-empty text as one warning rather than failing the workflow.

### 5. Good/Base/Bad Cases
- Good: 8 user-edited beats create one `chapter_expand` run, one `prose_markdown` artifact, one review artifact, and warning toasts only when review issues exist.
- Base: legacy `beat_expand` remains available for per-beat/internal expansion and keeps its `beat`, `beat_index`, `total_beats`, and `preceding_beats_prose` contract.
- Bad: looping over `beat_expand` from the editor as the default path after full-chapter expansion exists.
- Bad: allowing the review pass to block delivery of successfully generated prose.

### 6. Tests Required
- Prompt tests asserting the full-chapter writer includes ordered beat coverage, 3,000-5,000 character target, and forbidden-format rules.
- Pipeline tests asserting `chapter_expand` stores `prose_markdown`, stores `chapter_expand_review`, parses review issues into warnings, and keeps prose delivery when review fails.
- Worker/context tests asserting request-level Style/Plot profile overrides are injected into the runtime prompt context.
- Prompt Stack tests asserting the full `beats` list participates in runtime activation.
- Frontend client/hook tests asserting one `chapter_expand` workflow call replaces the previous per-beat loop and surfaces review warnings after delivery.

### 7. Wrong vs Correct

#### Wrong
Add a new prose prompt and only update the frontend hook, leaving `NovelWorkflowIntentType`, generated OpenAPI types, artifacts, and prompt-stack activation unaware of the new intent.

#### Correct
Update the Pydantic workflow request contract, pipeline handler, prompt builders, artifacts, warnings, worker activation context, generated OpenAPI output, frontend API client, hook behavior, and deterministic tests in the same change.

## Scenario: TXT Novel Import And Imported Chapter Rewrite

### 1. Scope / Trigger
- Trigger: changing TXT import, imported chapter persistence, imported full-chapter rewrite, or selected-chapter enrichment rewrite APIs.
- This is a cross-layer contract: upload validation, import draft storage, project creation, `outline_detail`, `project_chapters`, Novel Workflow intent handling, generated OpenAPI, frontend import wizard, and editor rewrite UI must stay aligned.

### 2. Signatures
- Import preview: `POST /api/v1/novel-imports/preview` with multipart fields `project_name`, `default_provider_id`, optional `default_model`, optional `style_profile_id`, optional `plot_profile_id`, optional `generation_profile`, `length_preset`, `rights_confirmed`, and `file`.
- Import draft update: `PATCH /api/v1/novel-imports/{draft_id}` with project metadata and ordered chapter drafts.
- Import commit: `POST /api/v1/novel-imports/{draft_id}/commit` returning `project_id`.
- Rewrite job create: `POST /api/v1/novel-chapter-rewrite-jobs` with `project_id`, `chapter_id`, and free-form `instruction`.
- Rewrite job read/apply: `GET /status`, `GET /logs`, `GET /artifact`, and `POST /apply` under `/api/v1/novel-chapter-rewrite-jobs/{job_id}`.
- Normal-project workflow intent: `intent_type="chapter_enrichment_rewrite"`; artifact name: `chapter_rewrite_markdown`.
- TXT-imported workflow intent: `intent_type="imported_chapter_full_rewrite"`; artifact name: `chapter_rewrite_markdown`.

### 3. Contracts
- Import requires explicit `rights_confirmed=true`; the product must not fetch or advertise arbitrary third-party book rewriting.
- Import drafts are short-lived server-side JSON documents keyed by generated UUIDs; route draft ids must be normalized as UUIDs before path construction.
- TXT parsing should split common chapter headings and return a single editable chapter plus warning when no standard headings exist.
- Commit must create a normal project, write parser-compatible `outline_detail`, sync chapters, then write imported chapter `content` and `word_count`.
- Rewrite jobs wrap the existing Novel Workflow worker and must not mutate chapter content until `apply`.
- For `project_origin="txt_import_rewrite"`, rewrite job creation must route to `imported_chapter_full_rewrite`; normal projects continue to route to `chapter_enrichment_rewrite`.
- The imported full-rewrite prompt must use the current chapter as the only rewrite target, with previous chapter tail and next chapter head as boundary context.
- The imported full-rewrite prompt must not inject full `outline_detail`, `story_summary`, runtime bible sections, `Chapter Objective Card`, `Intensity Profile`, `Runtime Guardrails`, or Plot Writing Guide by default.
- Voice Profile may be injected as language/style reference only.
- Active character extraction for imported full rewrite is optional support for selecting relevant character material; if no match is found, omit the block instead of emitting fallback prose.
- Trace metadata for imported full rewrite must expose the `imported_chapter_adjacent_window_v1` context policy and injected context sizes.
- `apply` may replace the chapter content only after the rewrite workflow has succeeded and the artifact is non-empty.

### 4. Validation & Error Matrix
- Missing rights confirmation -> `422 请先确认你拥有处理该 TXT 内容的权利`.
- Non-`.txt` upload or unsupported content type -> `422`.
- Empty TXT -> `422 上传的 TXT 文件为空`.
- Oversized upload -> upload-cleaning validation error; do not write a draft.
- Invalid, expired, or cross-user draft id -> `404 导入草稿不存在或已过期`.
- Empty imported chapter title -> `422 章节标题不能为空`.
- Empty target chapter -> `422 当前章节正文为空，无法改写`.
- Oversized target chapter for v1 rewrite -> `422 当前章节过长，v1 暂不支持自动分块改写`.
- Applying a non-succeeded rewrite job or empty artifact -> `409`.
- Direct `imported_chapter_full_rewrite` workflow creation for a non-`txt_import_rewrite` project -> reject before generation.
- Imported full-rewrite output that is empty, meta commentary, non-prose, below 30% original length, or copies the next chapter boundary -> fail the workflow.
- Imported full-rewrite output with suspicious but reviewable drift, such as 180%-300% length or possible chapter-title retention -> store workflow warnings and append job logs.

### 5. Good/Base/Bad Cases
- Good: a user uploads an authorized TXT, confirms parsed chapters, commits a new project, rewrites one selected chapter, previews the artifact, and applies it explicitly.
- Good: imported project chapter rewrite uses `imported_chapter_full_rewrite`, injects adjacent chapter windows, and outputs only the rewritten chapter body without the chapter title.
- Base: a no-heading TXT imports as one chapter with a warning and remains editable before commit.
- Bad: constructing draft file paths from unvalidated route params.
- Bad: directly overwriting chapter content when the rewrite job is created or when the artifact is generated.
- Bad: using `assemble_writing_context()` or a generated `Chapter Objective Card` for imported full rewrite, because imported outline navigation is not a real plot plan and can make the model continue into later chapter events.
- Bad: treating next-chapter context as generation material instead of a boundary guard.

### 6. Tests Required
- Import tests for valid split headings, no-heading fallback, rights confirmation, non-TXT/empty/oversized uploads, invalid draft ids, and commit chapter ordering/content.
- Rewrite job tests for create validation, artifact generation/storage, status/log/artifact reads, non-succeeded apply rejection, and successful apply updating `content` and `word_count`.
- Imported full-rewrite tests for project-origin intent routing, direct-origin gate, adjacent-window prompt inclusion, planning-context exclusion, trace manifest metadata, deterministic validation fatal cases, and warning cases.
- API/OpenAPI contract tests proving frontend client payloads match backend schemas.
- Frontend tests for import wizard preview/update/commit, warning display, rewrite dialog progress/preview, and explicit apply.

### 7. Wrong vs Correct

#### Wrong
Treat import drafts as arbitrary filenames or let frontend code chain project creation, outline sync, and chapter writes manually.

#### Correct
Validate draft ids as generated UUIDs, keep import commit in a backend service transaction boundary, and expose one commit API that produces a normal project plus normal `project_chapters`.

#### Wrong
Use the chapter rewrite endpoint as a direct update endpoint that replaces content immediately.

#### Correct
Persist rewrite output as `chapter_rewrite_markdown` first; require a separate apply call to mutate the selected chapter.

#### Wrong
Route imported project full-chapter rewrites through `chapter_enrichment_rewrite` and the shared writing-context assembler.

#### Correct
Route imported project full-chapter rewrites through `imported_chapter_full_rewrite`, use the imported adjacent-window prompt builder, and keep full-project planning context disabled.

### Bible planning asset dependency contract

When changing novel-planning prompts or workflow intents, preserve the upstream asset order:

`characters_blueprint` (角色索引与关系网) -> `outline_master` -> `volume_generate` -> `volume_chapters_generate` / `outline_detail`.

- `characters_blueprint` is the upstream character graph, not a loose character bio dump.
- `outline_master` must consume the character graph and cover character function slots, conflict slots, reward slots, resistance slots, and foreshadowing slots.
- Volume and chapter planning prompts may only do local expansion. They must not rewrite the global character network.
- If an upstream planning asset is missing, user messages should mark the gap as a placeholder / recommended prerequisite instead of letting the model invent a complete replacement system.
- Backend labels and frontend prerequisites must stay aligned when this order changes.

### Novel profile injection contract

When changing novel prompts, preserve the profile injection matrix:

- Structural planning assets (`world_building`, `characters_blueprint`, `outline_master`, `outline_detail`, `volume_generate`, `volume_chapters_generate`) must inject Plot Writing Guide and Generation Profile, but must not inject Voice Profile. Voice samples are language references and should not steer world rules, character facts, or outline structure.
- Beat planning (`beat_generate`) must inject Plot Writing Guide and Generation Profile, but must not inject Voice Profile because it produces planning beats rather than prose.
- Reader-facing concept generation must not inject Voice Profile or Generation Profile runtime constraints. It may include Plot Writing Guide only as a narrowed structure reference for story promise, pressure shape, and payoff rhythm; do not use the shared `append_profile_blocks()` helper because that adds prose/planning contracts that are too heavy for concept cards.
- Prose generation and rewriting surfaces (`beat_expand`, `assemble_writing_context()` consumers) may inject both Voice Profile and Plot Writing Guide. Voice Profile is strongest at the language layer only and must not override project facts, character relationships, plot direction, format, or safety boundaries.
- Prompt asset initialization must stay free of Style/Plot injection; generated assets should not duplicate or rewrite mounted Style/Plot profiles.

### Generation profile compatibility boundaries

- Keep `GENERATION_PROFILE_ADAPTER` strict for the canonical discriminated union contract.
- If persisted or UI-derived project/workflow payloads need compatibility cleanup, centralize it in `prompt_profiles.py` and reuse it from every schema boundary that accepts or returns `generation_profile`.
- Current compatibility rule: `target_market="mainstream"` may discard only the legacy/intensity keys `desire_overlays` and `intensity_level`; unrelated extra keys must still raise Pydantic validation errors.
- Regression tests must cover project create/update/response paths, workflow create requests, and direct persisted-state helpers such as `validate_generation_profile()`.

---

## Testing Requirements

- Core business logic changes require relevant `pytest` coverage.
- Async tests must remain compatible with `pytest-asyncio` strict mode.
- Database tests must preserve isolation through truncation or transaction rollback.
- API integration tests should use `TestClient` or `AsyncClient` and cover important Pydantic validation boundaries.
- LLM state machine, API, and persistence tests should use mock data builders by default.
- Live provider tests are reserved for prompt accuracy or structured-output boundary checks and must read credentials from `PERSONA_TEST_PROVIDER_*` environment variables.
- Long representative text samples belong in fixture/resource files loaded by pytest fixtures.

For planning prompt or workflow dependency changes, add or update prompt contract tests that assert:

- the upstream asset is explicitly present in the system prompt or user message,
- the novel profile injection matrix is preserved for each changed prompt surface,
- missing upstream assets produce placeholder guidance,
- changed helper signatures are reflected at every call site,
- frontend prerequisite metadata matches backend Bible field semantics when labels or ordering change.

---

## Code Review Checklist

- Router, Service, and Repository responsibilities remain separated.
- Prompt, parser, Pydantic schema, OpenAPI output, frontend types, and tests are synchronized.
- Query loading prevents N+1 behavior on relationship access.
- Large data paths stream or batch instead of loading everything into memory.
- Error and logging paths do not leak secrets.
