"""Runtime prompt registry."""

from __future__ import annotations

from app.prompts.common import PromptLane, PromptSpec

PROMPT_SPECS: tuple[PromptSpec, ...] = (
    PromptSpec(
        id="editor.section",
        lane=PromptLane.EDITOR,
        output_contract="markdown",
        test_focus="section-specific instructions, style/plot injection, length presets",
    ),
    PromptSpec(
        id="editor.volume",
        lane=PromptLane.EDITOR,
        output_contract="markdown",
        test_focus="volume planning format and regeneration guidance",
    ),
    PromptSpec(
        id="editor.memory_sync",
        lane=PromptLane.EDITOR,
        output_contract="two-heading markdown parsed into BibleUpdateResponse",
        test_focus="runtime state and thread headings stay parser-compatible",
    ),
    PromptSpec(
        id="editor.beat",
        lane=PromptLane.EDITOR,
        output_contract="markdown",
        test_focus="beat list format, plot/style injection, chapter pressure progression",
    ),
    PromptSpec(
        id="editor.concept",
        lane=PromptLane.EDITOR,
        output_contract="markdown concept blocks parsed into ConceptItem list",
        test_focus="three-card strategy and concept block parseability",
    ),
    PromptSpec(
        id="style.chunk_analysis",
        lane=PromptLane.STYLE_ANALYSIS,
        output_contract="markdown",
        test_focus="markdown-only style evidence sections and chunk context",
    ),
    PromptSpec(
        id="style.voice_profile",
        lane=PromptLane.STYLE_ANALYSIS,
        output_contract="markdown",
        test_focus="voice profile with fixed writing-only sections and no story controls",
    ),
    PromptSpec(
        id="plot.sketch",
        lane=PromptLane.PLOT_ANALYSIS,
        output_contract="json",
        test_focus="PlotChunkSketch fields and JSON-only exception",
    ),
    PromptSpec(
        id="plot.analysis",
        lane=PromptLane.PLOT_ANALYSIS,
        output_contract="markdown",
        test_focus="markdown plot evidence sections and skeleton context",
    ),
    PromptSpec(
        id="plot.story_engine",
        lane=PromptLane.PLOT_ANALYSIS,
        output_contract="markdown",
        test_focus="story engine profile with fixed pursuit mechanics and overlay suggestions",
    ),
)

_PROMPT_SPECS_BY_ID = {spec.id: spec for spec in PROMPT_SPECS}


def get_prompt_spec(prompt_id: str) -> PromptSpec:
    """Return registry metadata for a runtime prompt id."""

    return _PROMPT_SPECS_BY_ID[prompt_id]


__all__ = ["PROMPT_SPECS", "PromptLane", "PromptSpec", "get_prompt_spec"]
