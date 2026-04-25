from __future__ import annotations

from app.prompts import PROMPT_SPECS, PromptLane, get_prompt_spec


def test_prompt_registry_has_unique_complete_specs() -> None:
    ids = [spec.id for spec in PROMPT_SPECS]

    assert len(ids) == len(set(ids))
    assert {spec.lane for spec in PROMPT_SPECS} == {
        PromptLane.EDITOR,
        PromptLane.STYLE_ANALYSIS,
        PromptLane.PLOT_ANALYSIS,
    }

    for spec in PROMPT_SPECS:
        assert spec.id
        assert spec.output_contract
        assert spec.test_focus


def test_prompt_registry_can_lookup_existing_runtime_prompt() -> None:
    spec = get_prompt_spec("plot.story_engine")

    assert spec.lane is PromptLane.PLOT_ANALYSIS
    assert spec.output_contract == "markdown"
    assert spec.test_focus == "story engine profile with fixed pursuit mechanics and overlay suggestions"
