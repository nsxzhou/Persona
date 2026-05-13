from __future__ import annotations

import pytest


def test_build_numbered_chapter_rewrite_source_numbers_non_empty_paragraphs() -> None:
    from app.services.chapter_rewrite_patches import build_numbered_chapter_rewrite_source

    assert build_numbered_chapter_rewrite_source(
        "  第一段。  \n \t\n第二段。\n\n# 内容内标题"
    ) == "[P001]\n第一段。\n\n[P002]\n第二段。\n\n[P003]\n# 内容内标题"


def test_parse_chapter_rewrite_plan_accepts_yaml_front_matter() -> None:
    from app.services.chapter_rewrite_patches import parse_chapter_rewrite_plan

    plan = parse_chapter_rewrite_plan(
        """---
edits:
  - operation: insert_after
    paragraph_id: P001
    new_text: |-
      新增段落。

      新增第二段。
  - operation: replace
    paragraph_id: P003
    new_text: |-
      替换后的第三段。
---
"""
    )

    assert [(edit.operation, edit.paragraph_id, edit.new_text) for edit in plan.edits] == [
        ("insert_after", "P001", "新增段落。\n\n新增第二段。"),
        ("replace", "P003", "替换后的第三段。"),
    ]


@pytest.mark.parametrize(
    ("output", "message"),
    [
        ("", "输出为空"),
        ("edits: []", "YAML front matter"),
        ("---\nedits: []\n---\n\nNotes", "之外的正文"),
        ("---\n[]\n---", "顶层必须是对象"),
        ("---\nedits: []\n---", "非空列表"),
        (
            """---
edits:
  - operation: insert_after
    paragraph_id: P001
---""",
            "缺少 new_text",
        ),
        (
            """---
edits:
  - operation: delete
    paragraph_id: P001
    new_text: |-
      删除。
---""",
            "操作不支持",
        ),
        (
            """---
edits:
  - operation: insert_after
    paragraph_id: 1
    new_text: |-
      新增。
---""",
            "paragraph_id 格式不正确",
        ),
        (
            """---
edits:
  - operation: insert_after
    paragraph_id: P001
    new_text: |-
      新增一。
  - operation: replace
    paragraph_id: P001
    new_text: |-
      新增二。
---""",
            "重复使用",
        ),
    ],
)
def test_parse_chapter_rewrite_plan_rejects_invalid_output(
    output: str,
    message: str,
) -> None:
    from app.services.chapter_rewrite_patches import parse_chapter_rewrite_plan

    with pytest.raises(ValueError, match=message):
        parse_chapter_rewrite_plan(output)


def test_apply_chapter_rewrite_plan_insert_after_and_replace_in_original_order() -> None:
    from app.services.chapter_rewrite_patches import (
        apply_chapter_rewrite_plan,
        parse_chapter_rewrite_plan,
    )

    plan = parse_chapter_rewrite_plan(
        """---
edits:
  - operation: replace
    paragraph_id: P003
    new_text: |-
      第三段改写。新增很多字。
  - operation: insert_after
    paragraph_id: P001
    new_text: |-
      第一段后新增。
---"""
    )

    result = apply_chapter_rewrite_plan(
        "第一段。\n\n第二段。\n\n第三段。",
        plan,
        expansion_ratio_percent=100,
    )

    assert result == "第一段。\n\n第一段后新增。\n\n第二段。\n\n第三段改写。新增很多字。"


def test_apply_chapter_rewrite_plan_preserves_unchanged_whitespace_separators() -> None:
    from app.services.chapter_rewrite_patches import (
        apply_chapter_rewrite_plan,
        parse_chapter_rewrite_plan,
    )

    plan = parse_chapter_rewrite_plan(
        """---
edits:
  - operation: insert_after
    paragraph_id: P002
    new_text: |-
      新增段落。
---"""
    )

    result = apply_chapter_rewrite_plan(
        " 第一段。 \n \t\n第二段。",
        plan,
        expansion_ratio_percent=20,
    )

    assert result == " 第一段。 \n \t\n第二段。\n\n新增段落。"


def test_apply_chapter_rewrite_plan_rejects_missing_paragraph_id_atomically() -> None:
    from app.services.chapter_rewrite_patches import (
        apply_chapter_rewrite_plan,
        parse_chapter_rewrite_plan,
    )

    plan = parse_chapter_rewrite_plan(
        """---
edits:
  - operation: insert_after
    paragraph_id: P999
    new_text: |-
      新增段落。
---"""
    )

    with pytest.raises(ValueError, match="paragraph_id 不存在"):
        apply_chapter_rewrite_plan(
            "第一段。\n\n第二段。",
            plan,
            expansion_ratio_percent=20,
        )


def test_apply_chapter_rewrite_plan_allows_growth_above_budget() -> None:
    from app.services.chapter_rewrite_patches import (
        apply_chapter_rewrite_plan,
        parse_chapter_rewrite_plan,
    )

    plan = parse_chapter_rewrite_plan(
        """---
edits:
  - operation: insert_after
    paragraph_id: P001
    new_text: |-
      新增内容。新增内容。新增内容。新增内容。新增内容。
---"""
    )

    result = apply_chapter_rewrite_plan(
        "1234567890\n\n第二段。",
        plan,
        expansion_ratio_percent=20,
    )

    assert "新增内容。" in result


def test_apply_chapter_rewrite_plan_rejects_growth_below_budget() -> None:
    from app.services.chapter_rewrite_patches import (
        apply_chapter_rewrite_plan,
        parse_chapter_rewrite_plan,
    )

    plan = parse_chapter_rewrite_plan(
        """---
edits:
  - operation: replace
    paragraph_id: P001
    new_text: |-
      1234567890
---"""
    )

    with pytest.raises(ValueError, match="扩写字数低于预算"):
        apply_chapter_rewrite_plan(
            "1234567890\n\n第二段。",
            plan,
            expansion_ratio_percent=20,
        )
