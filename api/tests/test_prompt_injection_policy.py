from __future__ import annotations

from app.services.prompt_injection import PromptInjectionMode
from app.services.prompt_injection_policy import (
    PromptInjectionTask,
    resolve_injection_mode,
)
from app.services.llm_provider import LLMProviderService


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
        PromptInjectionTask.STYLE_ANALYSIS_VOICE_PROFILE,
        PromptInjectionTask.PLOT_ANALYSIS_SKELETON,
        PromptInjectionTask.PLOT_ANALYSIS_SKELETON_GROUP,
        PromptInjectionTask.PLOT_ANALYSIS_CHUNK,
        PromptInjectionTask.PLOT_ANALYSIS_MERGE,
        PromptInjectionTask.PLOT_ANALYSIS_REPORT,
        PromptInjectionTask.PLOT_ANALYSIS_STORY_ENGINE,
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


def test_llm_provider_temperature_uses_layered_defaults_per_task() -> None:
    service = LLMProviderService()

    assert service._resolve_temperature(injection_task=PromptInjectionTask.PROVIDER_CONNECTION_TEST) == 0.0
    assert service._resolve_temperature(injection_task=PromptInjectionTask.EDITOR_CHAPTER_SUMMARY) == 0.0
    assert service._resolve_temperature(injection_task=PromptInjectionTask.EDITOR_BIBLE_UPDATE) == 0.1
    assert service._resolve_temperature(injection_task=PromptInjectionTask.EDITOR_SECTION_GENERATION) == 0.4
    assert service._resolve_temperature(injection_task=PromptInjectionTask.EDITOR_BEAT_GENERATION) == 0.4
    assert service._resolve_temperature(injection_task=PromptInjectionTask.EDITOR_VOLUME_GENERATION) == 0.4
    assert service._resolve_temperature(injection_task=PromptInjectionTask.EDITOR_VOLUME_CHAPTERS_GENERATION) == 0.4
    assert service._resolve_temperature(injection_task=PromptInjectionTask.EDITOR_CONTINUATION) == 0.7
    assert service._resolve_temperature(injection_task=PromptInjectionTask.EDITOR_BEAT_EXPANSION) == 0.7
    assert service._resolve_temperature(injection_task=PromptInjectionTask.EDITOR_CONCEPT_GENERATION) == 0.9


def test_llm_provider_temperature_falls_back_to_default_for_unmapped_task() -> None:
    service = LLMProviderService()

    assert service._resolve_temperature(injection_task=PromptInjectionTask.STYLE_ANALYSIS_CHUNK) == 0.7


def test_llm_provider_temperature_defaults_when_task_missing() -> None:
    service = LLMProviderService()

    assert service._resolve_temperature(injection_task=None) == 0.7
