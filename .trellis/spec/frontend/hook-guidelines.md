# Hook Guidelines

> How hooks are used in this project.

---

## Overview

Hooks hold reusable client-side stateful logic. Data-fetching hooks should respect the project's Server Component, Server Action, and TanStack Query boundaries.

---

## Custom Hook Patterns

- Custom hooks must start with `use`.
- Keep hooks focused on one state or data-flow concern.
- Do not import server-only modules from hooks used by Client Components.
- Tests that render hooks using React Query should create a fresh `QueryClient` per render unless the test intentionally verifies cache reuse.

---

## Data Fetching

- Prefer Server Components with `async/await` for initial server-side reads.
- Use TanStack Query for browser-side cache, refresh, retry, and interactive mutations.
- Use Server Actions directly for simple server mutations with route revalidation.
- When a mutation needs loading feedback, errors, manual invalidation, retry, or optimistic behavior, pass the Server Action or API call as the React Query `mutationFn`.

## Scenario: Project prompt asset hooks

### 1. Scope / Trigger
- Trigger: project-scoped CRUD or preview APIs used from a workbench tab.
- These hooks cross API client, React Query cache, form state, and route-level project state.

### 2. Signatures
- Query key family:
  - `projectKeys.promptAssets(projectId)`
- Hooks:
  - `useProjectPromptAssetsQuery(projectId)`
  - `useCreateProjectPromptAsset()`
  - `useUpdateProjectPromptAsset()`
  - `useDeleteProjectPromptAsset()`
  - `useApplyProjectPromptAssetSuggestions()`
  - `usePreviewProjectPromptStack()`

### 3. Contracts
- CRUD mutations must invalidate `projectKeys.promptAssets(projectId)`.
- Applying prompt asset suggestions must invalidate `projectKeys.promptAssets(projectId)` after the backend writeback succeeds.
- Preview is a mutation, not a query, because it depends on transient user-entered context and should not be treated as cached project state.
- Prompt asset initialization generation runs through `prompt_asset_init` Novel Workflow and reads the `prompt_asset_suggestions` artifact; do not cache suggestion artifacts as project state.
- Chapter-scoped form fields must send `chapter_id`; project-scoped forms must send `chapter_id: null`.
- Editor workflow hooks that create Novel Workflow runs must thread the selected `chapterId` through to the API payload when a selected chapter exists.

### 4. Validation & Error Matrix
- Empty asset title -> UI blocks save before API call.
- `scope = chapter` without selected chapter -> UI blocks save before API call.
- Preview chapter selector cleared -> send `chapter_id: null`.
- Mutation failure -> preserve current form state and surface a toast.
- Suggestion apply failure -> preserve the generated suggestion list so the user can retry or inspect it.

### 5. Good/Base/Bad Cases
- Good: saving an asset invalidates the asset list and keeps the selected created asset open.
- Good: confirming initialization suggestions refreshes the asset list and clears the suggestion preview.
- Base: preview with no selected chapter still shows project-scoped/always-on assets.
- Bad: sharing a module-level `QueryClient` in tests causes chapter data to leak between editor tests.
- Bad: writing suggestions into a frontend-only local asset list without invalidating the server query leaves preview/runtime out of sync.

### 6. Tests Required
- API client contract tests for prompt asset CRUD and preview paths.
- API client contract tests for `prompt_asset_init` artifact fetch and `apply-suggestions`.
- Workbench tab tests that verify the Prompt Stack tab mounts and uses asset hooks.
- Editor tests that verify selected `chapterId` reaches selection rewrite, beat generation, and beat expansion workflows.
- Tests that render React Query components should create a fresh `QueryClient` per render unless the test explicitly validates cache reuse.

### 7. Wrong vs Correct

#### Wrong
Use a shared module-level `QueryClient` in a component test file and call `queryClient.clear()` in `beforeEach`.

#### Correct
Construct a fresh `QueryClient` inside the test render helper so query observers and async cache updates cannot leak across tests.

---

## Naming Conventions

- Hook names must begin with `use`.
- Query hooks should include the domain and resource they fetch, for example `useProjectPromptAssetsQuery`.
- Mutation hooks should name the write operation, for example `useCreateProjectPromptAsset`.
- Query key helpers should be centralized by domain so RSC prefill, hooks, invalidation, and tests share the same key shape.

---

## Common Mistakes

- Sharing a module-level `QueryClient` in tests.
- Treating transient preview inputs as cached server state.
- Forgetting to invalidate the relevant query key after a mutation.
- Dropping route or chapter context when threading workflow payloads through hooks.
