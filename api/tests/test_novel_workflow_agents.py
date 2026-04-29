from __future__ import annotations

import pytest


def test_novel_workflow_agents_are_split_into_named_components() -> None:
    from app.services.novel_workflow_agents import (
        ActiveCharactersAgent,
        BeatAgent,
        ContextSelectorAgent,
        ContinuityAgent,
        EditorAgent,
        MemorySyncAgent,
        Orchestrator,
        OutlineAgent,
        WorldBuildingAgent,
    )

    orchestrator = Orchestrator()
    assert orchestrator.select_intent_node("project_bootstrap") == "run_project_bootstrap"
    assert orchestrator.select_intent_node("chapter_write") == "run_chapter_write"
    assert orchestrator.select_intent_node("concept_bootstrap") == "run_concept_bootstrap"

    context = ContextSelectorAgent().select(
        {
            "project_description": "desc",
            "current_bible": {
                "world_building": "world",
                "characters_blueprint": "chars",
                "outline_master": "master",
                "outline_detail": "detail",
                "characters_status": "status",
                "runtime_state": "state",
                "runtime_threads": "threads",
            },
        }
    )
    assert context["description"] == "desc"
    assert context["runtime_threads"] == "threads"

    for agent in (
        OutlineAgent,
        WorldBuildingAgent,
        ActiveCharactersAgent,
        BeatAgent,
        ContinuityAgent,
        EditorAgent,
        MemorySyncAgent,
    ):
        assert agent.__module__ == "app.services.novel_workflow_agents"


def test_continuity_editor_and_memory_prompts_are_owned_by_agent_modules() -> None:
    from app.prompts.continuity import build_continuity_system_prompt
    from app.prompts.final_editor import build_editor_polish_system_prompt
    from app.prompts.memory_sync import build_story_summary_system_prompt

    assert "## Verdict" in build_continuity_system_prompt()
    assert "绝不改变剧情事实" in build_editor_polish_system_prompt()
    assert "GLOBAL_SUMMARY_UPDATED" in build_story_summary_system_prompt()


class StubLLM:
    def __init__(self, output: str) -> None:
        self.output = output
        self.calls: list[dict[str, str]] = []

    async def __call__(
        self,
        *,
        system_prompt: str,
        user_context: str,
        mode: str,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_context": user_context,
                "mode": mode,
            }
        )
        return self.output


@pytest.mark.asyncio
async def test_active_characters_agent_parses_json_array_and_limits_input() -> None:
    from app.services.novel_workflow_agents import ActiveCharactersAgent

    llm = StubLLM('["沈砚", " 林栖 ", 7, "沈砚"]')
    names = await ActiveCharactersAgent(llm).extract(
        text_before_cursor="前" * 2500,
        current_chapter_context="章" * 4500,
    )

    assert names == ["沈砚", "林栖"]
    assert len(llm.calls[0]["user_context"]) < 6500
    assert llm.calls[0]["mode"] == "analysis"


@pytest.mark.asyncio
async def test_active_characters_agent_parses_fenced_json_array() -> None:
    from app.services.novel_workflow_agents import ActiveCharactersAgent

    names = await ActiveCharactersAgent(StubLLM('```json\n["阿蛮"]\n```')).extract(
        text_before_cursor="阿蛮推门而入。",
        current_chapter_context="",
    )

    assert names == ["阿蛮"]


@pytest.mark.asyncio
async def test_active_characters_agent_returns_empty_list_for_invalid_output() -> None:
    from app.services.novel_workflow_agents import ActiveCharactersAgent

    names = await ActiveCharactersAgent(StubLLM("沈砚、林栖")).extract(
        text_before_cursor="沈砚看向林栖。",
        current_chapter_context="",
    )

    assert names == []


@pytest.mark.asyncio
async def test_active_characters_agent_returns_empty_list_when_llm_fails() -> None:
    from app.services.novel_workflow_agents import ActiveCharactersAgent

    async def failing_llm(**_: str) -> str:
        raise RuntimeError("temporary extraction failure")

    names = await ActiveCharactersAgent(failing_llm).extract(
        text_before_cursor="沈砚看向林栖。",
        current_chapter_context="",
    )

    assert names == []
