# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This directory contains authoritative backend guidelines for Persona's FastAPI, SQLAlchemy, Pydantic, Alembic, and LLM workflow code.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Router, Service, Repository, schema, and worker organization | Active |
| [Database Guidelines](./database-guidelines.md) | Async SQLAlchemy 2.0, transactions, migrations, and loading patterns | Active |
| [Error Handling](./error-handling.md) | Domain errors, propagation, and API responses | Active |
| [Quality Guidelines](./quality-guidelines.md) | Typing, Pydantic V2, LLM state machines, memory, and tests | Active |
| [Logging Guidelines](./logging-guidelines.md) | Business and exception logging expectations | Active |

---

## Pre-Development Checklist

1. Read `.trellis/spec/guides/agent-workflow-guidelines.md`.
2. Read `directory-structure.md` before changing routers, services, repositories, schemas, dependencies, or workers.
3. Read `database-guidelines.md` before changing models, repositories, migrations, transactions, query loading, or batch work.
4. Read `error-handling.md` and `logging-guidelines.md` before changing service exceptions or exception handlers.
5. Read `quality-guidelines.md` before changing prompts, Pydantic schemas, LLM workflows, state machines, tests, or large data processing.

---

**Language**: All documentation should be written in **English**.
