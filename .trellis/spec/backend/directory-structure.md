# Directory Structure

> How backend code is organized in this project.

---

## Overview

Persona backend code uses Python 3.11+, FastAPI, async SQLAlchemy 2.0, Pydantic V2, and Alembic. Keep Router, Service, and Repository responsibilities strictly separated.

---

## Directory Layout

```text
api/app/
├── api/
│   ├── deps.py              # Annotated FastAPI dependency aliases
│   └── routes/              # HTTP endpoints only
├── core/                    # settings, security, domain errors, shared core helpers
├── db/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── session.py           # async engine/session factory
│   └── repositories/        # direct database access
├── prompts/                 # LLM prompt templates and parsers
├── schemas/                 # Pydantic request/response/structured-output contracts
├── services/                # business logic and workflow orchestration
└── worker.py                # background worker entrypoint
```

---

## Module Organization

- Router modules under `api/app/api/routes/` receive requests, declare dependencies, call one service operation, and format response schemas.
- Service modules under `api/app/services/` own business logic, workflow orchestration, transaction boundaries, and coordination across repositories or external services.
- Repository modules under `api/app/db/repositories/` only perform direct database CRUD and query loading.
- Pydantic schemas under `api/app/schemas/` define request, response, and structured LLM output contracts.
- Prompt templates and parsers under `api/app/prompts/` must stay aligned with the schemas they describe.
- Shared dependency aliases belong in `api/app/api/deps.py` and should use `Annotated[..., Depends(...)]`.

## Layer Rules

- Do not write complex business logic or database queries directly in Router functions.
- Do not expose SQLAlchemy query/session details from Repository APIs to callers.
- Do not put external HTTP calls or cross-domain business decisions in Repositories.
- Worker code that needs backend logic should reuse Services instead of duplicating Router behavior.
- Service dependencies should be explicit through constructors or `deps.py`, not fetched from FastAPI request state inside service methods.

---

## Naming Conventions

- Use modern Python 3.11+ typing: `list[str]`, `dict[str, Any]`, and `str | None`.
- Every function should have explicit parameter and return types.
- Keep module names aligned with the domain they implement, for example route, service, repository, and schema files for the same feature should use the same domain vocabulary.

---

## Examples

- `api/app/api/routes/projects.py` for a thin Router.
- `api/app/services/projects.py` for service-level business logic.
- `api/app/db/repositories/projects.py` for repository-level SQLAlchemy access.
- `api/app/api/deps.py` for `Annotated` dependency aliases.
