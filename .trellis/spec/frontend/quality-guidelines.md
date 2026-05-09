# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

Frontend changes must preserve RSC boundaries, generated type contracts, form validation, cache behavior, Tailwind/shadcn consistency, and build-time App Router correctness.

---

## Forbidden Patterns

- Adding `'use client'` to high-level layouts or pages unless the whole file truly needs client behavior.
- Importing `server-only` modules into Client Components or client hooks.
- Passing non-serializable props across the Server/Client boundary.
- Duplicating generated API DTOs with hand-written interfaces.
- Using `npm` or `yarn` in `web/`; use `pnpm`.
- Replacing React Query mutation state or React 19 form hooks with unnecessary manual loading/error boilerplate.

---

## Required Patterns

- Use `vitest` and React Testing Library for core UI components, hooks, API clients, and complex client logic.
- Mock Next.js-specific APIs such as `useRouter` when testing Client Components.
- Validate Server/Client rendering boundaries by running `pnpm build` for relevant App Router or RSC changes.
- Use a local server/browser check when changing complex front-end workflow state or wizard interactions.

---

## Testing Requirements

<!-- What level of testing is expected -->

### Markdown artifact parsers

When the UI depends on a backend-generated Markdown artifact format, keep the parser as a pure function under `web/lib/` and test it separately from the component.

- Parse only the documented/current format unless the task explicitly asks for legacy compatibility.
- Return a failure value (for example `null`) instead of guessing when required headings, tables, or fenced blocks are missing.
- The component must provide a safe fallback, usually the raw Markdown artifact.
- Unit tests must cover a valid artifact, malformed input, and fenced code content that itself contains backticks.

This prevents generic Markdown previews from becoming hidden data contracts and avoids fragile UI-only parsing logic.

---

## Code Review Checklist

- RSC and Client Component boundaries are intentional.
- API DTOs come from OpenAPI-generated types.
- Mutations invalidate the right React Query keys.
- Form validation exists on both client and Server Action/backend boundaries.
- `pnpm build` was run when route, RSC, or serialization behavior changed.
