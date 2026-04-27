from __future__ import annotations


def test_novel_workflow_agents_are_split_into_named_components() -> None:
    from app.services.novel_workflow_agents import (
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
