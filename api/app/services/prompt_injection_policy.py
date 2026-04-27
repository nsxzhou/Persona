from __future__ import annotations

from enum import StrEnum

from app.services.prompt_injection import PromptInjectionMode


class PromptInjectionTask(StrEnum):
    PROVIDER_CONNECTION_TEST = "provider.connection_test"
    EDITOR_CONTINUATION = "editor.continuation"
    EDITOR_SECTION_GENERATION = "editor.section_generation"
    EDITOR_BEAT_EXPANSION = "editor.beat_expansion"
    EDITOR_BIBLE_UPDATE = "editor.bible_update"
    EDITOR_CHAPTER_SUMMARY = "editor.chapter_summary"
    EDITOR_BEAT_GENERATION = "editor.beat_generation"
    EDITOR_CONCEPT_GENERATION = "editor.concept_generation"
    EDITOR_VOLUME_GENERATION = "editor.volume_generation"
    EDITOR_VOLUME_CHAPTERS_GENERATION = "editor.volume_chapters_generation"
    STYLE_ANALYSIS_CHUNK = "style_analysis.chunk"
    STYLE_ANALYSIS_MERGE = "style_analysis.merge"
    STYLE_ANALYSIS_REPORT = "style_analysis.report"
    STYLE_ANALYSIS_VOICE_PROFILE = "style_analysis.voice_profile"
    PLOT_ANALYSIS_SKETCH = "plot_analysis.sketch"
    PLOT_ANALYSIS_SKELETON = "plot_analysis.skeleton"
    PLOT_ANALYSIS_SKELETON_GROUP = "plot_analysis.skeleton_group"
    PLOT_ANALYSIS_CHUNK = "plot_analysis.chunk"
    PLOT_ANALYSIS_MERGE = "plot_analysis.merge"
    PLOT_ANALYSIS_REPORT = "plot_analysis.report"
    PLOT_ANALYSIS_STORY_ENGINE = "plot_analysis.story_engine"


_TASK_TO_MODE: dict[PromptInjectionTask, PromptInjectionMode] = {
    PromptInjectionTask.PROVIDER_CONNECTION_TEST: "none",
    PromptInjectionTask.EDITOR_CONTINUATION: "immersion",
    PromptInjectionTask.EDITOR_SECTION_GENERATION: "analysis",
    PromptInjectionTask.EDITOR_BEAT_EXPANSION: "immersion",
    PromptInjectionTask.EDITOR_BIBLE_UPDATE: "analysis",
    PromptInjectionTask.EDITOR_CHAPTER_SUMMARY: "analysis",
    PromptInjectionTask.EDITOR_BEAT_GENERATION: "analysis",
    PromptInjectionTask.EDITOR_CONCEPT_GENERATION: "analysis",
    PromptInjectionTask.EDITOR_VOLUME_GENERATION: "analysis",
    PromptInjectionTask.EDITOR_VOLUME_CHAPTERS_GENERATION: "analysis",
    PromptInjectionTask.STYLE_ANALYSIS_CHUNK: "analysis",
    PromptInjectionTask.STYLE_ANALYSIS_MERGE: "analysis",
    PromptInjectionTask.STYLE_ANALYSIS_REPORT: "analysis",
    PromptInjectionTask.STYLE_ANALYSIS_VOICE_PROFILE: "analysis",
    PromptInjectionTask.PLOT_ANALYSIS_SKETCH: "none",
    PromptInjectionTask.PLOT_ANALYSIS_SKELETON: "analysis",
    PromptInjectionTask.PLOT_ANALYSIS_SKELETON_GROUP: "analysis",
    PromptInjectionTask.PLOT_ANALYSIS_CHUNK: "analysis",
    PromptInjectionTask.PLOT_ANALYSIS_MERGE: "analysis",
    PromptInjectionTask.PLOT_ANALYSIS_REPORT: "analysis",
    PromptInjectionTask.PLOT_ANALYSIS_STORY_ENGINE: "analysis",
}


def resolve_injection_mode(task: PromptInjectionTask) -> PromptInjectionMode:
    return _TASK_TO_MODE[task]


__all__ = ["PromptInjectionTask", "resolve_injection_mode"]
