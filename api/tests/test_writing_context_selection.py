from __future__ import annotations


def _character_cards(prefix: str, count: int) -> str:
    return "\n\n".join(
        f"## 角色{i}\n- {prefix}正文：ROLE_{i}\n- 关系：只属于角色{i}"
        for i in range(1, count + 1)
    )


def test_select_writing_context_keeps_only_active_character_bodies() -> None:
    from app.services.writing_context_selection import select_writing_context

    selected = select_writing_context(
        current_bible={
            "characters_blueprint": _character_cards("蓝图", 30),
            "characters_status": _character_cards("状态", 30),
            "world_building": "世界规则",
        },
        active_character_names=["角色3", "角色20"],
        current_chapter_context="",
        text_before_cursor="",
    )

    assert "ROLE_3" in selected.characters_blueprint
    assert "ROLE_20" in selected.characters_blueprint
    assert "ROLE_8" not in selected.characters_blueprint
    assert "- 角色8" in selected.characters_blueprint
    assert "ROLE_3" in selected.active_character_focus
    assert "ROLE_20" in selected.active_character_focus


def test_select_writing_context_falls_back_to_first_cards_when_no_active_match() -> None:
    from app.services.writing_context_selection import select_writing_context

    selected = select_writing_context(
        current_bible={
            "characters_blueprint": _character_cards("蓝图", 9),
            "characters_status": _character_cards("状态", 9),
        },
        active_character_names=[],
        current_chapter_context="没有明确角色名",
        text_before_cursor="",
    )

    assert "ROLE_1" in selected.characters_blueprint
    assert "ROLE_6" in selected.characters_blueprint
    assert "ROLE_7" not in selected.characters_blueprint
    assert "- 角色7" in selected.characters_blueprint


def test_select_writing_context_applies_static_and_character_budgets() -> None:
    from app.services.writing_context_selection import select_writing_context

    selected = select_writing_context(
        current_bible={
            "world_building": "世" * 6000,
            "outline_master": "纲" * 5000,
            "outline_detail": "章" * 9000,
            "runtime_state": "态" * 7000,
            "runtime_threads": "线" * 7000,
            "story_summary": "摘" * 6000,
            "characters_blueprint": "## 角色A\n" + ("A" * 3000),
            "characters_status": "## 角色A\n" + ("S" * 3000),
        },
        active_character_names=["角色A"],
        current_chapter_context="",
        text_before_cursor="",
    )

    assert len(selected.world_building) <= 4000
    assert len(selected.outline_master) <= 3000
    assert len(selected.outline_detail) <= 7000
    assert len(selected.runtime_state) <= 5000
    assert len(selected.runtime_threads) <= 4000
    assert len(selected.story_summary) <= 4000
    assert "A" * 1500 not in selected.characters_blueprint
    assert "S" * 1500 not in selected.characters_status
