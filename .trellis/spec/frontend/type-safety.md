# Type Safety

> Type safety patterns in this project.

---

## Overview

Frontend TypeScript API DTOs must use generated OpenAPI types as the single source of truth. Runtime form validation uses Zod.

---

## Type Organization

- `web/lib/api/generated/openapi.ts` is generated from the backend OpenAPI schema.
- `web/lib/types.ts` may alias or derive business names from generated OpenAPI schemas.
- Hand-written types are allowed for pure UI ViewModels, local display composition, and state labels with no matching backend schema.
- Do not maintain hand-written API response DTOs alongside generated OpenAPI DTOs.

---

## Validation

- Use `react-hook-form` with Zod for strict form state and validation.
- Server Actions must validate incoming data again with Zod.
- Keep frontend Zod constraints aligned with backend Pydantic constraints.

---

## Common Patterns

- Use `Pick`, `Omit`, intersections, or helper aliases over generated OpenAPI types when a UI needs a narrowed or composed shape.
- Regenerate OpenAPI output after backend schema or route response changes before repairing frontend references.

---

## Forbidden Patterns

- Duplicating API response shapes as hand-written interfaces.
- Keeping generated and hand-written API DTOs in parallel.
- Updating frontend hand-written types as a temporary workaround for stale OpenAPI output.
- Weakening optional or nullable semantics to silence TypeScript errors.
