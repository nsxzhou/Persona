"""Outline parser unit tests."""

import pytest

from app.services.outline_parser import parse_outline, insert_chapters_into_volume


class TestParseOutline:
    def test_multi_volume(self):
        md = (
            "## 第一卷：黎明之前\n"
            "> 主题：觉醒与出发\n\n"
            "### 第 1 章：开端\n"
            "- **核心事件**：起点\n"
            "- **情绪走向**：平静\n"
            "- **章末钩子**：悬念\n\n"
            "## 第二卷：暴风前夜\n"
            "> 主题：成长\n"
        )
        result = parse_outline(md)
        assert len(result["volumes"]) == 2
        assert result["volumes"][0]["title"] == "第一卷：黎明之前"
        assert result["volumes"][0]["meta"] == "主题：觉醒与出发"
        assert result["volumes"][0]["body_markdown"] == "> 主题：觉醒与出发"
        assert len(result["volumes"][0]["chapters"]) == 1
        assert result["volumes"][0]["chapters"][0]["core_event"] == "起点"
        assert result["volumes"][0]["chapters"][0]["emotion_arc"] == "平静"
        assert result["volumes"][0]["chapters"][0]["chapter_hook"] == "悬念"
        assert len(result["volumes"][1]["chapters"]) == 0

    def test_empty_string(self):
        result = parse_outline("")
        assert len(result["volumes"]) == 0
        assert len(result["parse_errors"]) == 0

    def test_unparseable(self):
        result = parse_outline("random text without structure")
        assert len(result["volumes"]) == 0
        assert len(result["parse_errors"]) > 0

    def test_legacy_chapter_end_push_field_is_still_parsed_as_hook(self):
        md = (
            "## 第一卷：旧格式\n\n"
            "### 第 1 章：开端\n"
            "- **核心事件**：起点\n"
            "- **情绪走向**：平静\n"
            "- **章节末推动点**：旧字段也要兼容\n"
        )

        result = parse_outline(md)

        assert len(result["volumes"]) == 1
        assert result["volumes"][0]["chapters"][0]["chapter_hook"] == "旧字段也要兼容"

    def test_ignores_top_level_title_and_volume_level_h3_sections(self):
        md = (
            "# 《最后三个月》全书分卷规划\n\n"
            "## 第一卷：撕掉标签（第1-8章）\n\n"
            "> 主题：当系统抛弃你之前，你先抛弃系统 | 当前压力：诊断书+母亲期待\n\n"
            "### 主驱动轴\n"
            "力量与权力的初次解放。\n\n"
            "### 本卷核心兑现物\n"
            "**规则的第一次被打破**：庄晏当着班主任的面说“我自愿堕落”。\n\n"
            "### 第 1 章：诊断书\n"
            "- **核心事件**：庄晏拿到诊断书\n"
            "- **情绪走向**：麻木 → 压抑\n"
            "- **章末钩子**：他决定退学\n\n"
            "## 全篇闭环验证\n\n"
            "| 要素 | 验证结果 |\n"
            "|------|---------|\n"
            "| 开局压制 | 诊断书 |\n"
        )

        result = parse_outline(md)

        assert result["parse_errors"] == []
        assert len(result["volumes"]) == 1
        assert result["volumes"][0]["title"] == "第一卷：撕掉标签（第1-8章）"
        assert "### 主驱动轴" in result["volumes"][0]["body_markdown"]
        assert "### 本卷核心兑现物" in result["volumes"][0]["body_markdown"]
        assert len(result["volumes"][0]["chapters"]) == 1
        assert result["volumes"][0]["chapters"][0]["title"] == "第 1 章：诊断书"

    def test_short_chapter_only_format_still_works(self):
        md = (
            "### 第 1 章：开端\n"
            "- **核心事件**：起点\n\n"
            "### 第 2 章：发展\n"
            "- **核心事件**：升级\n"
        )

        result = parse_outline(md)

        assert result["parse_errors"] == []
        assert len(result["volumes"]) == 1
        assert result["volumes"][0]["title"] == ""
        assert result["volumes"][0]["body_markdown"] == ""
        assert [chapter["title"] for chapter in result["volumes"][0]["chapters"]] == [
            "第 1 章：开端",
            "第 2 章：发展",
        ]


class TestInsertChaptersIntoVolume:
    def test_inserts_chapters_at_correct_position(self):
        original = (
            "## 第一卷：黎明\n"
            "> 主题：觉醒\n\n"
            "## 第二卷：暴风\n"
            "> 主题：成长\n"
        )
        chapters_md = (
            "### 第 1 章：开端\n"
            "- **核心事件**：起点\n"
        )
        result = insert_chapters_into_volume(original, 0, chapters_md)
        assert "### 第 1 章：开端" in result
        assert result.index("### 第 1 章") < result.index("## 第二卷")

    def test_appends_chapters_to_last_volume(self):
        original = "## 第一卷：测试\n> 主题：测试\n"
        chapters_md = "### 第 1 章：开端\n- **核心事件**：起点\n"
        result = insert_chapters_into_volume(original, 0, chapters_md)
        assert "### 第 1 章：开端" in result
