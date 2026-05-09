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
- Reader-facing concept generation may inject both Voice Profile and Plot Writing Guide; use the shared `append_profile_blocks()` Voice wrapper instead of ad hoc `Style Prompt Pack` text.
- Prose generation and rewriting surfaces (`beat_expand`, `assemble_writing_context()` consumers) may inject both Voice Profile and Plot Writing Guide. Voice Profile is strongest at the language layer only and must not override project facts, character relationships, plot direction, format, or safety boundaries.
- Prompt asset initialization must stay free of Style/Plot injection; generated assets should not duplicate or rewrite mounted Style/Plot profiles.

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
