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

### Motion System

- Use the global motion utilities from `web/app/globals.css` for interactive transitions and entry animation:
  - `.motion-button` for buttons, icon buttons, and compact clickable controls.
  - `.motion-input` for form controls and focusable field wrappers.
  - `.motion-surface` for cards or panels that can hover/lift, with `data-interactive="true"` only when the whole surface is clickable.
  - `.motion-panel` for non-clickable panels, badges, popovers, and compact status surfaces.
  - `.motion-row` for table, list, chapter tree, and queue rows.
  - `.animate-fade-in`, `.animate-slide-up`, and `.animate-scale-in` for restrained entry states.
- Prefer these utilities over ad hoc `transition-*`, `duration-*`, and `ease-*` classes when adding or touching UI motion.
- Do not apply transform-writing entry animations such as `.animate-slide-up` or `.animate-scale-in` to elements whose positioning depends on Tailwind transform utilities, for example fixed centered Radix dialog content using `translate-x-[-50%] translate-y-[-50%]`. Use `.animate-fade-in` there so positioning transforms are preserved.
- Keep production/editor surfaces restrained: apply motion to rows, panels, width changes, and button feedback, not large page-level effects that distract from repeated writing workflows.

---

## Accessibility

Use the accessibility behavior provided by shadcn/ui primitives and preserve labels, focus states, keyboard behavior, and ARIA attributes when wrapping them.

---

## Common Mistakes

- Adding `'use client'` at a page or layout root when only one child needs state.
- Passing functions or complex instances from Server Components into Client Components.
- Recreating base UI primitives outside `components/ui/`.
- Concatenating Tailwind strings by hand and introducing class conflicts.
