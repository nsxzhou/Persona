from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from app.services.context_assembly import WritingPromptAssetLayer
from app.services.novel_workflow_agents import BeatAgent, ConceptAgent, MemorySyncAgent
from app.services.novel_workflow_storage import NovelWorkflowStorageService


NovelWorkflowState = dict[str, Any]
SimpleIntentHandler = Callable[
    [NovelWorkflowState, dict[str, str], Any],
    Awaitable[dict[str, Any]],
]


class NovelWorkflowPipelineContext(Protocol):
    storage_service: NovelWorkflowStorageService
    beat_agent: BeatAgent
    concept_agent: ConceptAgent
    memory_sync_agent: MemorySyncAgent

    async def _call_prompt(
        self,
        *,
        system_prompt: str,
        user_context: str,
        mode: str,
        prompt_stack_manifest: dict | None = None,
    ) -> str: ...

    async def _select_writing_context(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
    ) -> Any: ...

    async def _select_imported_rewrite_character_context(
        self,
        state: NovelWorkflowState,
        current_bible: dict[str, str],
        chapter_content: str,
    ) -> Any: ...

    def _generation_profile_obj(self, state: NovelWorkflowState) -> Any: ...


def state_prompt_stack_manifest(state: dict[str, Any]) -> dict | None:
    prompt_stack = state.get("prompt_stack")
    manifest = getattr(prompt_stack, "manifest", None)
    if manifest is None:
        return None
    if hasattr(manifest, "model_dump"):
        return manifest.model_dump(mode="json")
    if isinstance(manifest, dict):
        return manifest
    return None


def state_prompt_asset_layers(state: dict[str, Any]) -> list[WritingPromptAssetLayer]:
    prompt_stack = state.get("prompt_stack")
    layers = getattr(prompt_stack, "layers", None)
    if not isinstance(layers, list):
        return []
    return [
        WritingPromptAssetLayer(
            key=layer.key,
            title=layer.title,
            content=layer.content,
        )
        for layer in layers
        if getattr(layer, "key", "") in {
            "active_lorebook_entries",
            "active_character_cards",
            "author_notes",
        }
    ]
