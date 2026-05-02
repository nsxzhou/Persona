from __future__ import annotations

from app.services.prose_validation import validate_limited_third_prose


def test_validate_limited_third_prose_flags_bracketed_inner_monologue() -> None:
    issues = validate_limited_third_prose("庄晏停了一下。（心想：不能再待了。）")

    assert issues == ["检测到限制性第三人称违规表达"]


def test_validate_limited_third_prose_flags_first_person_inner_thoughts() -> None:
    issues = validate_limited_third_prose("我心想，这事不能拖。")

    assert issues == ["检测到限制性第三人称违规表达"]


def test_validate_limited_third_prose_allows_observable_third_person() -> None:
    issues = validate_limited_third_prose("庄晏抬眼看向门口，指节慢慢收紧。")

    assert issues == []
