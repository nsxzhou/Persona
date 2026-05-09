# Frontend Development Guidelines

> Best practices for frontend development in this project.

---

## Overview

This directory contains authoritative frontend guidelines for Persona's Next.js App Router, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, and generated API contracts.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | App Router, component, hook, lib, and API-client organization | Active |
| [Component Guidelines](./component-guidelines.md) | RSC boundaries, props, composition, Tailwind, shadcn/ui | Active |
| [Hook Guidelines](./hook-guidelines.md) | Custom hooks, data fetching, React Query, mutations | Active |
| [State Management](./state-management.md) | Local, server, optimistic, and form state | Active |
| [Quality Guidelines](./quality-guidelines.md) | Testing, forbidden patterns, RSC/build checks | Active |
| [Type Safety](./type-safety.md) | OpenAPI single source of truth, Zod, validation | Active |

---

## Pre-Development Checklist

1. Read `.trellis/spec/guides/agent-workflow-guidelines.md`.
2. Read `directory-structure.md` before moving files or adding routes, components, hooks, API clients, or lib helpers.
3. Read `component-guidelines.md` before changing RSC boundaries, Client Components, props, styling, or shadcn/ui usage.
4. Read `hook-guidelines.md` and `state-management.md` before changing React Query, Server Actions, forms, optimistic updates, or shared state.
5. Read `type-safety.md` before changing API payloads, OpenAPI-generated types, `web/lib/types.ts`, or Zod schemas.
6. Read `quality-guidelines.md` before adding tests or touching App Router build boundaries.

---

**Language**: All documentation should be written in **English**.
