from __future__ import annotations

import ast
from pathlib import Path


PROMPT_ROOT = Path(__file__).resolve().parents[1] / "app" / "prompts"


def test_agent_prompt_modules_exist_and_own_prompt_builders() -> None:
    expected = {
        "concept.py": {
            "parse_concept_response",
            "build_concept_generate_system_prompt",
            "build_concept_generate_user_message",
        },
        "world_building.py": {
            "build_world_building_system_prompt",
            "build_world_building_user_message",
        },
        "characters.py": {
            "build_character_blueprint_system_prompt",
            "build_character_blueprint_user_message",
        },
        "outline.py": {
            "build_outline_master_system_prompt",
            "build_outline_master_user_message",
            "build_volume_generate_system_prompt",
            "build_volume_generate_user_message",
        },
        "chapter_plan.py": {
            "build_outline_detail_system_prompt",
            "build_outline_detail_user_message",
            "build_volume_chapters_system_prompt",
            "build_volume_chapters_user_message",
        },
        "beat.py": {
            "build_beat_generate_system_prompt",
            "build_beat_generate_user_message",
        },
        "prose_writer.py": {
            "build_beat_expand_system_prompt",
            "build_beat_expand_user_message",
        },
        "memory_sync.py": {
            "parse_bible_update_response",
            "build_bible_update_system_prompt",
            "build_bible_update_user_message",
            "build_chapter_summary_system_prompt",
            "build_chapter_summary_user_message",
            "build_story_summary_system_prompt",
        },
    }

    for filename, builders in expected.items():
        module_path = PROMPT_ROOT / filename
        assert module_path.exists(), filename
        tree = ast.parse(module_path.read_text())
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        assert builders <= function_names


def test_novel_prompt_methodology_is_embedded_in_agent_prompts() -> None:
    from app.prompts.beat import build_beat_generate_system_prompt
    from app.prompts.concept import build_concept_generate_system_prompt
    from app.prompts.section_router import build_section_system_prompt

    concept = build_concept_generate_system_prompt()
    characters = build_section_system_prompt("characters_blueprint")
    world = build_section_system_prompt("world_building")
    outline = build_section_system_prompt("outline_master")
    chapter_plan = build_section_system_prompt("outline_detail")
    beats = build_beat_generate_system_prompt()

    assert "核心DNA" in concept
    assert "当[主角+身份]遭遇[核心事件]，必须[关键行动]，否则[灾难后果]" in concept
    assert "表层目标、深层渴望、灵魂需求" in characters
    assert "初始状态 → 触发事件 → 认知失调 → 蜕变节点 → 最终状态" in characters
    assert "物理维度、社会维度、隐喻维度" in world
    assert "断层线" in world
    assert "三幕式" in outline
    assert "日常异常、催化事件、虚假胜利、灵魂黑夜、代价显现" in outline
    assert "3-5章构成一个悬念单元" in chapter_plan
    assert "认知过山车模式" in chapter_plan
    assert "伏笔三步法" in chapter_plan
    assert "认知颠覆" in beats
