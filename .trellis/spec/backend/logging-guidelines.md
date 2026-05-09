# Logging Guidelines

> How logging is done in this project.

---

## Overview

Use standard backend logging at important business nodes and exception boundaries. Logs should help diagnose workflow progress and failures without exposing user secrets or provider credentials.

---

## Log Levels

- Use `info` for major lifecycle events such as worker startup, job claim, workflow completion, and expected long-running stage transitions.
- Use `warning` for recoverable unexpected states, retries, skipped malformed optional data, or degraded behavior.
- Use `error` or exception logging for failures that abort a request, job, or workflow stage.
- Use `debug` only for local diagnostics that do not create noisy production logs.

---

## Structured Logging

- Include stable identifiers such as project id, run id, job id, provider id, or worker id when they are relevant.
- Prefer explicit fields or concise contextual messages over dumping whole ORM objects, prompts, request bodies, or provider responses.

---

## What to Log

- Critical business state changes.
- Background worker claim, heartbeat, retry, completion, and failure points.
- Exceptions at boundaries where context would otherwise be lost.
- External provider failures after redaction.

---

## What NOT to Log

- API keys, bearer tokens, cookies, encrypted provider secrets, or full URLs with secret query parameters.
- Full prompt payloads or generated long text unless the code path is explicitly a user-visible trace/audit artifact.
- Large uploaded files or large database result sets.
