# State Management

> How state is managed in this project.

---

## Overview

Keep state as close to its owner as possible. Server data belongs in Server Components or TanStack Query; interactive local UI state belongs in leaf Client Components.

---

## State Categories

- Server state: fetched backend data, cached through RSC rendering or TanStack Query.
- Local UI state: dialog open state, input draft state, selected tab, and other leaf interaction state.
- Form state: managed through `react-hook-form` plus Zod, or React 19 form hooks when no complex cache invalidation is needed.
- Optimistic state: handled with React 19 `useOptimistic` or React Query mutation patterns.

---

## When to Use Global State

Promote state only when multiple distant components truly need the same client-side value. Do not promote state just to avoid prop threading across a small component boundary.

---

## Server State

- Server Components should fetch initial data with `async/await`.
- Client Components should use TanStack Query for cached reads and mutations.
- Mutations that change backend state must invalidate or refresh the relevant query keys.
- Keep query keys consistent between RSC prefill and Client Component consumption.

---

## Common Mistakes

- Using `useState` loading/error boilerplate where React 19 form hooks or React Query already provide the state.
- Keeping a module-level `QueryClient` that leaks data between users or tests.
- Moving state to a top-level Client Component when only a leaf needs it.
