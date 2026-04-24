from __future__ import annotations

from app.services.prompt_injection import PromptInjectionMode
from app.services.prompt_injection_policy import (
    PromptInjectionTask,
    resolve_injection_mode,
)


def test_prompt_injection_policy_routes_editor_prose_tasks_to_immersion() -> None:
    assert resolve_injection_mode(PromptInjectionTask.EDITOR_CONTINUATION) == "immersion"
    assert resolve_injection_mode(PromptInjectionTask.EDITOR_BEAT_EXPANSION) == "immersion"


def test_prompt_injection_policy_routes_analysis_tasks_to_analysis() -> None:
    analysis_tasks = [
        PromptInjectionTask.EDITOR_SECTION_GENERATION,
        PromptInjectionTask.EDITOR_BEAT_GENERATION,
        PromptInjectionTask.EDITOR_CONCEPT_GENERATION,
        PromptInjectionTask.EDITOR_BIBLE_UPDATE,
        PromptInjectionTask.EDITOR_VOLUME_GENERATION,
        PromptInjectionTask.EDITOR_VOLUME_CHAPTERS_GENERATION,
        PromptInjectionTask.STYLE_ANALYSIS_CHUNK,
        PromptInjectionTask.STYLE_ANALYSIS_MERGE,
        PromptInjectionTask.STYLE_ANALYSIS_REPORT,
        PromptInjectionTask.STYLE_ANALYSIS_SUMMARY,
        PromptInjectionTask.STYLE_ANALYSIS_PROMPT_PACK,
        PromptInjectionTask.PLOT_ANALYSIS_SKELETON,
        PromptInjectionTask.PLOT_ANALYSIS_SKELETON_GROUP,
        PromptInjectionTask.PLOT_ANALYSIS_CHUNK,
        PromptInjectionTask.PLOT_ANALYSIS_MERGE,
        PromptInjectionTask.PLOT_ANALYSIS_REPORT,
        PromptInjectionTask.PLOT_ANALYSIS_SUMMARY,
        PromptInjectionTask.PLOT_ANALYSIS_PROMPT_PACK,
    ]

    for task in analysis_tasks:
        assert resolve_injection_mode(task) == "analysis"


def test_prompt_injection_policy_routes_strict_output_tasks_to_none() -> None:
    assert resolve_injection_mode(PromptInjectionTask.PROVIDER_CONNECTION_TEST) == "none"
    assert resolve_injection_mode(PromptInjectionTask.PLOT_ANALYSIS_SKETCH) == "none"


def test_prompt_injection_policy_returns_known_mode_literals() -> None:
    mode: PromptInjectionMode = resolve_injection_mode(
        PromptInjectionTask.EDITOR_CONTINUATION
    )
    assert mode in {"analysis", "immersion", "none"}
