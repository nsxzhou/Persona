from __future__ import annotations

import re


def build_continuity_system_prompt() -> str:
    return (
        "你是一位连续性审校 Agent。请检查正文是否与当前章节目标、角色状态、世界规则、运行时状态和伏笔追踪冲突。\n"
        "只输出 Markdown，必须包含以下标题：\n"
        "## Verdict\n## Conflicts\n## Character Drift\n## World Rule Issues\n## Required Rewrites\n"
        "Verdict 只能写 pass / fail / warning。"
    )


def build_continuity_user_message(
    *,
    prose_markdown: str,
    current_bible: dict[str, str],
    current_chapter_context: str,
    previous_chapter_context: str,
    beat: str | None,
) -> str:
    parts = [
        f"## 当前章节上下文\n\n{current_chapter_context}",
        f"## 前序章节上下文\n\n{previous_chapter_context}",
        f"## 当前运行时状态\n\n{current_bible.get('runtime_state', '')}",
        f"## 当前伏笔与线索追踪\n\n{current_bible.get('runtime_threads', '')}",
        f"## 当前角色动态状态\n\n{current_bible.get('characters_status', '')}",
    ]
    if beat:
        parts.append(f"## 当前节拍\n\n{beat}")
    parts.append(f"## 待检查正文\n\n{prose_markdown}")
    return "\n\n---\n\n".join(parts)


def extract_continuity_verdict(markdown: str) -> str:
    match = re.search(r"(?im)^## Verdict\s*(?:\n+|\s+)(pass|fail|warning)\b", markdown)
    if match:
        return match.group(1).lower()
    first_line = markdown.strip().splitlines()[0].strip().lower() if markdown.strip() else ""
    if first_line in {"pass", "fail", "warning"}:
        return first_line
    return "warning"
