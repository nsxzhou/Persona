# Agent Workflow Guidelines

> Cross-layer rules for AI-assisted development in this project.

---

## Scope

These rules apply before and during any code change, regardless of whether the change touches backend, frontend, prompts, tests, or documentation.

---

## Package Managers

- Backend work under `api/` must use `uv`.
- Do not use `pip` directly for project dependency management.
- Do not hand-edit `requirements.txt` as the source of truth.
- Keep `api/uv.lock` aligned when backend dependencies change.
- Frontend work under `web/` must use `pnpm`.
- Do not use `npm` or `yarn` for this project.
- Keep `web/pnpm-lock.yaml` aligned when frontend dependencies change.

---

## Read Before Changing

- Before modifying code, search and read the current implementation and architecture around the target area.
- For business logic changes, also read the relevant Pydantic schemas, TypeScript interfaces or OpenAPI-derived types, and existing tests.
- When changing a constant, configuration value, prompt, schema, API payload, or generated contract, search for mirrored definitions and call sites before editing.

---

## No Guessing

- Do not invent APIs, fields, routes, or function signatures from memory.
- If a type or function signature is unclear, trace it to the source definition.
- If the first search does not find the definition, broaden the search before writing code.

---

## Minimal, Consistent Changes

- Change only what is required for the task.
- Do not refactor unrelated logic or alter core configuration unless the task requires it.
- Match surrounding naming, comments, module boundaries, and error-handling style.
- Prefer existing local helpers and established patterns over new abstractions.

---

## Prompt, Schema, And Contract Coupling

- LLM prompts and structured output schemas are a coupled contract.
- When either side changes, globally search for and update the matching prompt, Pydantic schema, parser, frontend type, generated OpenAPI type, and tests.
- Prompt descriptions of field names, types, optionality, and shape must match the Pydantic or parser contract.
- Backend schema or route response changes must update OpenAPI output before frontend references are repaired.
- Do not create temporary hand-written frontend DTOs that duplicate API response structures.

---

## Memory And Streaming Safety

- Do not load large uploaded text, large history sets, or large query results into memory in one step.
- Use streaming or batch processing for large database reads, file reads, and response bodies.
- Use bounded concurrency for highly concurrent tasks.

---

## Delivery And Verification

- Core business logic changes require relevant backend `pytest` coverage.
- Frontend UI, hook, or data-flow changes require relevant `vitest` coverage and, when appropriate, a local browser check.
- App Router or RSC boundary changes should be closed with `pnpm build`.
- Prompt/state-machine tests should use deterministic mocks by default.
- Live LLM tests are only for prompt accuracy or structured-output boundary validation; credentials must come from environment variables such as `PERSONA_TEST_PROVIDER_*`.
- Long text samples for tests must live in fixture/resource files and be loaded by tests, not hard-coded into Python test bodies.

---

## Trellis Context

- Load the relevant `.trellis/spec/` guidance before editing a package or layer.
- Treat `.trellis/spec/` as the authority for agent-facing development rules.
- Runtime, backup, workspace, and task scratch files under `.trellis/` are not part of normal code changes unless a task explicitly targets them.
