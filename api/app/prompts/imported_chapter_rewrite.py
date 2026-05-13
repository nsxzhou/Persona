from __future__ import annotations

import re
from typing import Any, Protocol


IMPORTED_CHAPTER_FULL_REWRITE_INTENT = "imported_chapter_full_rewrite"
IMPORTED_CONTEXT_POLICY = "imported_chapter_adjacent_window_v1"

_META_PREFACE_RE = re.compile(
    r"^\s*(?:好的|当然|以下是|这是|下面是|我将|已根据|根据你的要求|抱歉|对不起)",
    re.IGNORECASE,
)
_BULLET_LINE_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)]|[一二三四五六七八九十]+[、.])\s+")
_CHAPTER_TITLE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:第[一二三四五六七八九十百千万0-9]+[章节回幕卷]|Chapter\s+\d+)",
    re.IGNORECASE,
)


class ImportedRewriteState(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...


def build_imported_chapter_rewrite_system_prompt(
    *,
    voice_profile_markdown: str,
    active_character_focus: str,
    expansion_ratio_percent: int = 20,
) -> str:
    parts = [
        "# 导入章节 YAML 计划改写",
        "",
        "你正在改写 TXT 导入项目中的单个既有章节。原章节正文是唯一改写目标；章节标题仅用于定位，不属于补丁内容。",
        "",
        "## 输出契约",
        "- 只输出 YAML front matter 改写计划，不得输出改写后的完整章节。",
        "- 输出必须以 `---` 开始并以 `---` 结束；结束后不得有任何正文、说明、Notes 或 Markdown 内容。",
        "- YAML 顶层只能包含 `edits`，且 `edits` 必须是非空列表。",
        "- 每个 edit 必须包含 `operation`、`paragraph_id`、`new_text` 三个字段。",
        "- `operation` 只能是 `insert_after` 或 `replace`。",
        "- `paragraph_id` 必须引用用户消息中给出的单个原文段落编号，例如 `P003`；不得复制原文作为 Anchor。",
        "- 同一个 `paragraph_id` 在一次计划中最多出现一次。",
        "- `new_text` 必须使用 YAML 块文本 `|-`，不能为空，可以包含一个或多个新自然段。",
        "- `insert_after` 表示把 `new_text` 插入到该编号段落后；`replace` 表示只替换该编号对应的一个原始自然段。",
        "- 不得做句子级定位，不得一次替换多个原始段落，不得引用不存在的段落编号。",
        "- 所有 edits 会先整体校验，再按原章节段落顺序应用；不要依赖输出顺序表达章节顺序。",
        f"- 合成后的净增长目标是原文字数的 {expansion_ratio_percent}%，允许上下 20% 浮动。",
        "- 不输出解释、修改清单、分析过程、元评论、JSON 或完整章节正文。",
        "- 保留原章节事实、事件顺序、视角、因果链、结果和结尾边界。",
        "- 用户指令只能在当前章节内增强、润色或补足，不得续写到下一章。",
        "- 如果用户要求补写省略场景，只能在原文已有省略、跳切、概述、淡出或省略号处扩展。",
        "- 下一章上下文只用于边界校准，不得作为 paragraph_id 或 new_text 出现在输出中。",
        "",
        "## 格式示例",
        "---",
        "edits:",
        "  - operation: insert_after",
        "    paragraph_id: P003",
        "    new_text: |-",
        "      <one or more new paragraphs>",
        "  - operation: replace",
        "    paragraph_id: P008",
        "    new_text: |-",
        "      <rewritten paragraph text>",
        "---",
        "",
        "## 禁用上下文",
        "- Plot Writing Guide disabled for this imported rewrite intent.",
        "- Bible sections disabled: Project Context, outline_detail, story_summary, runtime_state, runtime_threads, world_building, outline_master.",
    ]
    if voice_profile_markdown.strip():
        parts.extend(
            [
                "",
                "## Voice Profile（仅语言风格参考）",
                voice_profile_markdown.strip(),
            ]
        )
    if active_character_focus.strip():
        parts.extend(
            [
                "",
                "## Active Character Reference（低优先级角色参考）",
                active_character_focus.strip(),
            ]
        )
    return "\n".join(parts)


def build_imported_chapter_rewrite_user_context(
    *,
    target_title: str,
    chapter_content: str,
    previous_chapter: dict[str, str] | None,
    next_chapter: dict[str, str] | None,
    rewrite_instruction: str,
    expansion_ratio_percent: int = 20,
) -> str:
    parts: list[str] = []
    if target_title.strip():
        parts.append(f"## 目标章节标题（仅定位参考，不要输出）\n\n{target_title.strip()}")
    if previous_chapter is not None:
        previous_parts = [f"标题：{previous_chapter.get('title', '').strip()}"]
        if previous_chapter.get("summary", "").strip():
            previous_parts.append(f"摘要：{previous_chapter['summary'].strip()}")
        if previous_chapter.get("excerpt", "").strip():
            previous_parts.append(f"章末片段：\n{previous_chapter['excerpt'].strip()}")
        parts.append("## 上一章边界参考\n\n" + "\n\n".join(previous_parts))
    parts.append(f"## 编号后的当前章节原文（唯一改写目标）\n\n{chapter_content.strip()}")
    if next_chapter is not None:
        next_parts = [f"标题：{next_chapter.get('title', '').strip()}"]
        if next_chapter.get("summary", "").strip():
            next_parts.append(f"摘要：{next_chapter['summary'].strip()}")
        if next_chapter.get("excerpt", "").strip():
            next_parts.append(f"章首片段：\n{next_chapter['excerpt'].strip()}")
        parts.append("## 下一章边界参考（不得写入输出）\n\n" + "\n\n".join(next_parts))
    parts.append(
        "## 用户改写指令\n\n"
        f"{rewrite_instruction.strip() or '在不改变原章节事实和边界的前提下优化表达。'}\n\n"
        f"净增长目标：原文字数的 {expansion_ratio_percent}%，允许上下 20% 浮动。\n\n"
        "只输出当前章节的 YAML front matter 改写计划；不要输出章节标题或完整改写正文。"
    )
    return "\n\n---\n\n".join(parts)


def build_imported_context_manifest(
    *,
    state: ImportedRewriteState,
    chapter_content: str,
    previous_chapter: dict[str, str] | None,
    next_chapter: dict[str, str] | None,
    voice_profile_markdown: str,
    active_character_focus: str,
    active_character_names: list[str],
) -> dict[str, Any]:
    return {
        "intent": IMPORTED_CHAPTER_FULL_REWRITE_INTENT,
        "context_policy": IMPORTED_CONTEXT_POLICY,
        "target_chapter_id": state.get("chapter_id"),
        "target_chapter_title": state_chapter_title(state),
        "target_chapter_char_count": len(chapter_content),
        "previous_context_title": (previous_chapter or {}).get("title", ""),
        "previous_context_char_count": _adjacent_context_char_count(previous_chapter),
        "next_context_title": (next_chapter or {}).get("title", ""),
        "next_context_char_count": _adjacent_context_char_count(next_chapter),
        "voice_profile_injected": bool(voice_profile_markdown.strip()),
        "voice_profile_char_count": len(voice_profile_markdown.strip()),
        "plot_guide_disabled": True,
        "bible_sections_disabled": [
            "project_context",
            "outline_detail",
            "story_summary",
            "runtime_state",
            "runtime_threads",
            "world_building",
            "outline_master",
        ],
        "active_character_names": active_character_names,
        "active_character_material_char_count": len(active_character_focus),
}


def _adjacent_context_char_count(chapter: dict[str, str] | None) -> int:
    if chapter is None:
        return 0
    return sum(
        len(str(chapter.get(key) or "").strip())
        for key in ("title", "summary", "excerpt")
    )


def state_chapter_content(state: ImportedRewriteState) -> str:
    chapter_snapshot = state.get("chapter_snapshot")
    if isinstance(chapter_snapshot, dict):
        content = chapter_snapshot.get("content", "")
        if isinstance(content, str) and content.strip():
            return content
    return state.get("selected_text", "")


def state_chapter_title(state: ImportedRewriteState) -> str:
    chapter_snapshot = state.get("chapter_snapshot")
    if isinstance(chapter_snapshot, dict):
        title = chapter_snapshot.get("title", "")
        if isinstance(title, str) and title.strip():
            return title
    return state.get("current_chapter_context", "")


def state_imported_chapter(
    state: ImportedRewriteState,
    key: str,
) -> dict[str, str] | None:
    value = state.get(key)
    if not isinstance(value, dict):
        return None
    title = str(value.get("title") or "").strip()
    summary = str(value.get("summary") or "").strip()
    excerpt = str(value.get("excerpt") or "").strip()
    if not title and not summary and not excerpt:
        return None
    return {
        "id": str(value.get("id") or ""),
        "title": title,
        "summary": summary,
        "excerpt": excerpt,
    }


def validate_imported_chapter_rewrite_output(
    *,
    output: str,
    original: str,
    target_title: str,
    next_chapter: dict[str, str] | None,
    user_instruction: str,
) -> list[str]:
    text = output.strip()
    if not text:
        raise ValueError("导入章节改写输出为空")
    if _looks_like_meta_output(text):
        raise ValueError("导入章节改写输出包含模型说明或拒绝前言")
    if _looks_like_non_prose_output(text):
        raise ValueError("导入章节改写输出不是正文 prose 格式")
    if _includes_next_chapter_boundary(text, next_chapter):
        raise ValueError("导入章节改写输出疑似包含下一章标题或正文开头")

    original_length = max(len(original.strip()), 1)
    ratio = len(text) / original_length
    if ratio < 0.3:
        raise ValueError("导入章节改写输出长度低于原文 30%")
    if ratio > 3.0 and not _instruction_allows_expansion(user_instruction):
        raise ValueError("导入章节改写输出长度超过原文 300%")

    warnings: list[str] = []
    if 1.8 <= ratio <= 3.0:
        warnings.append("imported_rewrite_length_180_300_percent")
    if _appears_to_keep_chapter_title(text, target_title):
        warnings.append("imported_rewrite_possible_chapter_title")
    if _dialogue_or_action_removed(original, text):
        warnings.append("imported_rewrite_possible_dialogue_or_action_loss")
    if _ending_misaligned(original, text):
        warnings.append("imported_rewrite_possible_ending_misalignment")
    if _instruction_allows_expansion(user_instruction) and ratio >= 1.5:
        warnings.append("imported_rewrite_substantial_localized_expansion")
    return warnings


def _looks_like_meta_output(text: str) -> bool:
    first_line = text.splitlines()[0].strip()
    if _CHAPTER_TITLE_RE.match(first_line):
        return False
    return bool(_META_PREFACE_RE.match(first_line)) or "无法满足" in first_line


def _looks_like_non_prose_output(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith(("```", "|")):
        return True
    lines = [line for line in stripped.splitlines() if line.strip()]
    if not lines:
        return True
    bullet_lines = sum(1 for line in lines if _BULLET_LINE_RE.match(line))
    heading_lines = sum(1 for line in lines if line.lstrip().startswith("#"))
    if len(lines) <= 3 and (bullet_lines or heading_lines):
        return True
    return bullet_lines >= max(3, len(lines) // 2)


def _includes_next_chapter_boundary(
    text: str,
    next_chapter: dict[str, str] | None,
) -> bool:
    if next_chapter is None:
        return False
    title = next_chapter.get("title", "").strip()
    if title and title in text:
        return True
    excerpt = next_chapter.get("excerpt", "").strip()
    if not excerpt:
        return False
    compact_excerpt = _compact_text(excerpt)
    compact_output = _compact_text(text)
    substantial = compact_excerpt[:120]
    return len(substantial) >= 60 and substantial in compact_output


def _instruction_allows_expansion(user_instruction: str) -> bool:
    return any(
        keyword in user_instruction
        for keyword in ("补写", "扩写", "展开", "补全", "细写", "填补", "补足", "丰富")
    )


def _appears_to_keep_chapter_title(text: str, target_title: str) -> bool:
    first_line = text.splitlines()[0].strip()
    title = target_title.strip()
    return bool(_CHAPTER_TITLE_RE.match(first_line)) or bool(title and first_line == title)


def _dialogue_or_action_removed(original: str, output: str) -> bool:
    original_dialogue = original.count("“") + original.count('"')
    output_dialogue = output.count("“") + output.count('"')
    return original_dialogue >= 6 and output_dialogue <= original_dialogue * 0.35


def _ending_misaligned(original: str, output: str) -> bool:
    original_tail = _compact_text(original[-120:])
    output_tail = _compact_text(output[-240:])
    if len(original_tail) < 40:
        return False
    return original_tail[-40:] not in output_tail


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")
