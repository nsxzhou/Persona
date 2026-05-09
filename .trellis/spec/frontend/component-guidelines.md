# Component Guidelines

> How components are built in this project.

---

## Overview

Components default to React Server Components. Add `'use client'` only when a component actually needs React state, effects, event handlers, browser APIs, or client hooks.

---

## Component Structure

- Keep Pages and Layouts as Server Components unless client-only behavior is unavoidable.
- Push Client Components toward leaves of the tree to reduce client JavaScript.
- Files containing server-sensitive logic should use `import "server-only"`.
- Business components belong in `web/components/`; base primitives belong in `web/components/ui/`.

---

## Props Conventions

- Props passed from Server Components to Client Components must be serializable plain data.
- Do not pass class instances, database objects, unmarked functions, or non-serializable values across the RSC boundary.
- Server Actions may cross the boundary only through the supported `'use server'` mechanism.
- Use OpenAPI-derived types for API DTO props; use hand-written types only for pure UI ViewModels or display composition.

---

## Styling Patterns

- Use Tailwind CSS 4's CSS-first tokens through `@theme`.
- Avoid hard-coded magic style values when a project token exists.
- Use the `cn` helper for dynamic class names.
- Use `class-variance-authority` (`cva`) for components with multiple variants.
- Do not put deeply nested ternaries inside `cn()`.
- Reuse shadcn/ui primitives instead of rebuilding base inputs, buttons, dialogs, or similar controls.

---

## Accessibility

Use the accessibility behavior provided by shadcn/ui primitives and preserve labels, focus states, keyboard behavior, and ARIA attributes when wrapping them.

---

## Common Mistakes

- Adding `'use client'` at a page or layout root when only one child needs state.
- Passing functions or complex instances from Server Components into Client Components.
- Recreating base UI primitives outside `components/ui/`.
- Concatenating Tailwind strings by hand and introducing class conflicts.
