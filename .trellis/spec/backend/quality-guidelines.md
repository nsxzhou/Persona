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
