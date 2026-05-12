# Error Handling

> How errors are handled in this project.

---

## Overview

Business errors should be raised through the project's custom domain/HTTP exception mechanism and translated by the global FastAPI exception handler into a standard JSON response.

---

## Error Types

- Use the custom domain error family for business failures such as missing resources, invalid state transitions, ownership failures, and validation beyond Pydantic's built-in field checks.
- Use FastAPI/Pydantic validation for request shape and primitive bounds.
- Avoid raw `Exception` for expected business outcomes.

---

## Error Handling Patterns

- Services raise domain errors.
- Routers let domain errors bubble to the global handler.
- Do not catch a domain error in a Router only to re-raise `HTTPException`.
- Repository methods should not translate database or domain outcomes into HTTP responses.
- Rollback is handled by the request/session unit of work when exceptions propagate.
- `NotFoundError` messages for looked-up resources should include the stable lookup id
  used by that service, such as `project_id`, `job_id`, `run_id`, `provider_id`,
  or `asset_id`. For composite lookups, include each relevant id.

---

## API Error Responses

- Global exception handling must return the project's standard JSON error shape.
- Business error messages should be user-appropriate and consistent with nearby API messages.
- Do not leak secrets, provider tokens, or raw upstream error payloads to API clients.

---

## Common Mistakes

- Returning `500` for expected not-found or ownership failures.
- Duplicating exception translation in every Router.
- Logging or returning raw provider errors that may contain credentials.
- Raising vague resource lookup failures such as `"项目不存在"` from service methods when
  the service has the resource id available.
