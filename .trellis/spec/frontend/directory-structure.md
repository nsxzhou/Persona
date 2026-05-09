# Directory Structure

> How frontend code is organized in this project.

---

## Overview

Persona frontend uses Next.js App Router, React 19, TypeScript, Tailwind CSS 4, and shadcn/ui. Keep route files, reusable components, hooks, pure utilities, generated API types, and server-only code in their expected locations.

---

## Directory Layout

```text
web/
├── app/                  # Next.js route files: page.tsx, layout.tsx, route.ts, actions.ts
├── components/           # reusable business components
│   └── ui/               # shadcn/ui base components
├── hooks/                # custom React hooks
├── lib/                  # pure utilities, API clients, types, validations
│   ├── api/              # generated OpenAPI types and API transport helpers
│   ├── api.ts            # browser API requester
│   ├── server-api.ts     # server-only API requester
│   ├── types.ts          # OpenAPI-derived business aliases and UI-only types
│   └── validations/      # Zod schemas
└── vitest.setup.ts       # test setup
```

---

## Module Organization

- `app/` should contain route entrypoints and route-local Server Actions, not reusable UI libraries.
- `components/` contains reusable React components; `components/ui/` is for shadcn/ui primitives.
- `hooks/` contains reusable stateful client logic and React Query wrappers.
- `lib/` contains side-effect-light utilities, API clients, generated types, business type aliases, parsers, and validation schemas.
- Server-only files must import `server-only` when they contain sensitive server behavior or cookie-bearing backend calls.

---

## Naming Conventions

- Keep file names aligned with route or domain vocabulary.
- Custom hooks must start with `use`.
- Route actions should stay close to the route they mutate unless reused broadly.
- Generated API files should not be manually reshaped to hide backend contract changes.

---

## Examples

- `web/app/(workspace)/layout.tsx` for authenticated workspace RSC setup.
- `web/components/app-shell.tsx` for a reusable Client Component.
- `web/lib/server-api.ts` for server-only API access.
- `web/lib/types.ts` for OpenAPI-derived business type aliases.
