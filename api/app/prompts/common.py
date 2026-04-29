"""Shared helpers and metadata for runtime prompt builders."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PromptLane(StrEnum):
    """Runtime prompt domains with distinct quality priorities."""

    EDITOR = "editor"
    STYLE_ANALYSIS = "style_analysis"
    PLOT_ANALYSIS = "plot_analysis"


@dataclass(frozen=True)
class PromptSpec:
    """Lightweight registry metadata for a runtime prompt entrypoint."""

    id: str
    lane: PromptLane
    output_contract: str
    test_focus: str


REGENERATION_GUIDANCE = (
    "\n\n## 重新生成指令\n"
    "用户不满意上一版，现要求重新生成。\n"
    "- 【用户意见】非空时，用户意见的优先级高于上一版结果，必须逐条落实；\n"
    "- 以下方【上一版结果】为参考进行修订，但上一版不得压过用户意见；\n"
    "- 若用户要求改名、调整人物关系、剧情微调或改变风格，必须反映到正文/条目主体，不能只改标题、标签或表层包装；\n"
    "- 若【用户意见】为空，则只依据原上下文微调，不要完全推翻骨架；\n"
    "- 产出格式与首次生成保持一致。"
)


MARKDOWN_ONLY_RULE = "输出使用中文简体 Markdown，直接落正文/条目，不要写工作汇报，不要输出 JSON 或代码块。"
JSON_ONLY_RULE = "输出必须是一个合法 JSON 对象，只吐 JSON 本体；不要输出 Markdown、代码块、解释、寒暄或前后缀。"
NO_PREFACE_RULES = (
    "输出必须直接从指定模板的第一个标题开始。\n"
    "不要输出任何前言、任务说明、来源说明、总结或解释性开场，不要写工作汇报。\n"
    "不要写“好的”“下面是”“基于你提供的报告/摘要”“作为……我将……”这类句式。"
)
SCHEMA_ALIGNMENT_RULE = "Prompt 中声明的字段、标题和输出形状必须与对应 Pydantic Schema 或解析器保持一致。"
EVIDENCE_BOUNDARY_RULE = "所有结论必须证据优先；证据不足时明确声明，不得编造输入中不存在的事实。"


def join_prompt_parts(parts: list[str]) -> str:
    """Join prompt fragments without introducing accidental whitespace drift."""

    return "".join(parts)


def append_regeneration_context(
    parts: list[str],
    previous_output: str | None,
    user_feedback: str | None,
) -> None:
    """Append previous output and user feedback sections to user message parts."""

    if previous_output and previous_output.strip():
        parts.append(f"## 上一版结果\n\n{previous_output.strip()}")
    if user_feedback and user_feedback.strip():
        parts.append(f"## 用户意见（本次必须遵循）\n\n{user_feedback.strip()}")
