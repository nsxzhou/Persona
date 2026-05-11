from __future__ import annotations

import pytest


def test_parse_chapter_rewrite_patches_accepts_legal_markdown() -> None:
    from app.services.chapter_rewrite_patches import parse_chapter_rewrite_patches

    patches = parse_chapter_rewrite_patches(
        """# Chapter Rewrite Patches

## Patch 1
Operation: insert_after

Anchor:
```text
第一段。
```

New Text:
```text
新增段落。
```

## Patch 2
Operation: replace

Anchor:
```text
第二段。
```

New Text:
```text
替换后的第二段。
```
"""
    )

    assert [(patch.operation, patch.anchor, patch.new_text) for patch in patches] == [
        ("insert_after", "第一段。", "新增段落。"),
        ("replace", "第二段。", "替换后的第二段。"),
    ]


@pytest.mark.parametrize(
    ("markdown", "message"),
    [
        (
            """# Chapter Rewrite Patches

## Patch 1
Anchor:
```text
第一段。
```

New Text:
```text
新增段落。
```
""",
            "缺少 Operation",
        ),
        (
            """# Chapter Rewrite Patches

## Patch 1
Operation: delete

Anchor:
```text
第一段。
```

New Text:
```text
新增段落。
```
""",
            "操作不支持",
        ),
        (
            """# Chapter Rewrite Patches

## Patch 1
Operation: insert_after

New Text:
```text
新增段落。
```
""",
            "缺少 Anchor",
        ),
        (
            """# Chapter Rewrite Patches

## Patch 1
Operation: insert_after

Anchor:
```text
第一段。
```
""",
            "缺少 New Text",
        ),
        (
            """# Chapter Rewrite Patches

## Patch 1
extra
Operation: insert_after

Anchor:
```text
第一段。
```

New Text:
```text
新增段落。
```
""",
            "无法识别",
        ),
        (
            """# Chapter Rewrite Patches

## Patch 1
Operation: insert_after

extra
Anchor:
```text
第一段。
```

New Text:
```text
新增段落。
```
""",
            "无法识别",
        ),
        (
            """# Chapter Rewrite Patches

## Patch 1
Operation: insert_after

Anchor:
```text
第一段。
```

extra
New Text:
```text
新增段落。
```

extra
""",
            "无法识别",
        ),
        (
            """# Chapter Rewrite Patches

## Patch 1
Operation: insert_after

Anchor:
```
第一段。
```

New Text:
```text
新增段落。
```
""",
            "缺少 Anchor",
        ),
    ],
)
def test_parse_chapter_rewrite_patches_rejects_malformed_sections(
    markdown: str,
    message: str,
) -> None:
    from app.services.chapter_rewrite_patches import parse_chapter_rewrite_patches

    with pytest.raises(ValueError, match=message):
        parse_chapter_rewrite_patches(markdown)


def test_parse_chapter_rewrite_patches_rejects_no_patches() -> None:
    from app.services.chapter_rewrite_patches import parse_chapter_rewrite_patches

    with pytest.raises(ValueError, match="未返回任何可用补丁"):
        parse_chapter_rewrite_patches("# Chapter Rewrite Patches\n\nNo patches.")


def test_parse_chapter_rewrite_patches_allows_no_patches_text_inside_new_text() -> None:
    from app.services.chapter_rewrite_patches import parse_chapter_rewrite_patches

    patches = parse_chapter_rewrite_patches(
        """# Chapter Rewrite Patches

## Patch 1
Operation: insert_after

Anchor:
```text
第一段。
```

New Text:
```text
No patches.
```
"""
    )

    assert patches[0].new_text == "No patches."


def test_apply_chapter_rewrite_patches_insert_after_and_replace() -> None:
    from app.services.chapter_rewrite_patches import (
        ChapterRewritePatch,
        apply_chapter_rewrite_patches,
    )

    result = apply_chapter_rewrite_patches(
        "第一段。\n\n第二段。\n\n第三段。",
        [
            ChapterRewritePatch("replace", "第三段。", "第三段改写。新增很多字。"),
            ChapterRewritePatch("insert_after", "第一段。", "第一段后新增。"),
        ],
        expansion_ratio_percent=100,
    )

    assert result == "第一段。\n\n第一段后新增。\n\n第二段。\n\n第三段改写。新增很多字。"


@pytest.mark.parametrize(
    ("original", "patches", "message"),
    [
        (
            "第一段。\n\n第二段。",
            [("insert_after", "缺失段。", "新增段。")],
            "未在原章节中找到",
        ),
        (
            "第一段。\n\n第一段。",
            [("insert_after", "第一段。", "新增段。")],
            "出现多次",
        ),
        (
            "第一段。\n\n第二段。",
            [
                ("insert_after", "第一段。", "新增一。"),
                ("replace", "第一段。", "新增二。"),
            ],
            "重复使用",
        ),
        (
            "第一段。\n\n第二段。",
            [("replace", "第一段。\n\n第二段。", "替换。")],
            "只能定位一个自然段",
        ),
        (
            "第一段。\n\n第二段。",
            [("insert_after", "第一段。\n\n第二段。", "新增段。")],
            "只能定位一个自然段",
        ),
        (
            "第一段。\n\n第二段。",
            [("insert_after", "一段", "新增段。")],
            "完整自然段",
        ),
    ],
)
def test_apply_chapter_rewrite_patches_rejects_invalid_anchors(
    original: str,
    patches: list[tuple[str, str, str]],
    message: str,
) -> None:
    from app.services.chapter_rewrite_patches import (
        ChapterRewritePatch,
        apply_chapter_rewrite_patches,
    )

    with pytest.raises(ValueError, match=message):
        apply_chapter_rewrite_patches(
            original,
            [
                ChapterRewritePatch(operation, anchor, new_text)  # type: ignore[arg-type]
                for operation, anchor, new_text in patches
            ],
            expansion_ratio_percent=20,
        )


def test_apply_chapter_rewrite_patches_rejects_overlapping_or_contained_anchors() -> None:
    from app.services.chapter_rewrite_patches import (
        ChapterRewritePatch,
        apply_chapter_rewrite_patches,
    )

    with pytest.raises(ValueError, match="完整自然段|重叠|包含"):
        apply_chapter_rewrite_patches(
            "甲乙丙。\n\n第二段。",
            [
                ChapterRewritePatch("insert_after", "甲乙丙。", "新增段。"),
                ChapterRewritePatch("insert_after", "甲乙", "新增段。"),
            ],
            expansion_ratio_percent=20,
        )


def test_apply_chapter_rewrite_patches_rejects_budget_outside_tolerance() -> None:
    from app.services.chapter_rewrite_patches import (
        ChapterRewritePatch,
        apply_chapter_rewrite_patches,
    )

    with pytest.raises(ValueError, match="扩写字数超出预算"):
        apply_chapter_rewrite_patches(
            "1234567890\n\n第二段。",
            [ChapterRewritePatch("insert_after", "1234567890", "新增内容。")],
            expansion_ratio_percent=20,
        )
