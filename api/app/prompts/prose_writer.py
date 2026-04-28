from __future__ import annotations

from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context
from app.prompts.novel_shared import (
    BEAT_EXPAND_CONTEXT_CHARS,
    append_profile_blocks,
    get_hook_framework,
)
from app.schemas.prompt_profiles import GenerationProfile


def _build_beat_expand_system(beat_expand_chars: int = 500, hook_framework: str = "") -> str:
    return (
        "你是一位番茄金番作家，正在根据前文和给定节拍继续落正文。\n\n"
        "要求：\n"
        f"- 按照节拍描述展开约 {beat_expand_chars} 字的叙事段落\n"
        "- 保持与前文的语感和风格一致\n"
        "- 自然衔接前文，不要重复已有内容\n"
        "- 至少包含一个五感细节（视觉/听觉/嗅觉/触觉）\n"
        "- 对话部分要有潜台词，不直接说出意图\n"
        "- 段落控制在 150 字以内，适配移动端阅读\n"
        "- 动作/战斗场景用短句加快节奏\n"
        "- 每一段都要落下可感知的读者奖励（如极致的多巴胺爽感、金钱权力的兑现、或纯粹的生理与欲望满足）\n"
        "- 允许大段甚至整章的纯粹氛围、五感描写和欲望宣泄，充分满足读者的期待感与征服欲\n"
        "- 让读者体验主角正在享受绝对的权力掌控、彻底推倒高冷角色、或享受绝对忠诚的后宫陪伴\n"
        "- 主角内心的想法必须自然融入叙事或使用无引号的心理描写，绝不能在正文中使用括号（如“（...）”）来展示内心独白\n"
        "- 直接输出正文，绝不输出章节标题（如“# 第x章”），不要输出节拍本身、不要解释\n"
        f"{hook_framework}"
    )


def build_beat_expand_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    beat_expand_chars: int = 500,
    regenerating: bool = False,
) -> str:
    parts: list[str] = []
    append_profile_blocks(
        parts,
        style_prompt=style_prompt,
        plot_prompt=plot_prompt,
        plot_usage="续写只用于防止情节跑偏和洗白，不得复制样本角色、设定、事件或桥段。",
        generation_profile=generation_profile,
    )
    hook_framework = get_hook_framework(generation_profile)
    parts.append(_build_beat_expand_system(beat_expand_chars, hook_framework))
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_beat_expand_user_message(
    text_before_cursor: str,
    beat: str,
    beat_index: int,
    total_beats: int,
    preceding_beats_prose: str,
    outline_detail: str,
    runtime_state: str,
    runtime_threads: str,
    current_chapter_context: str = "",
    previous_chapter_context: str = "",
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    parts: list[str] = []
    if current_chapter_context.strip():
        parts.append(f"## 当前章节\n\n{current_chapter_context}")
    if outline_detail.strip():
        parts.append(f"## 章节细纲\n\n{outline_detail}")
    if runtime_state.strip():
        parts.append(f"## 运行时状态\n\n{runtime_state}")
    if runtime_threads.strip():
        parts.append(f"## 伏笔与线索追踪\n\n{runtime_threads}")
    if previous_chapter_context.strip():
        parts.append(f"## 前序章节\n\n{previous_chapter_context}")
    recent = (
        text_before_cursor[-BEAT_EXPAND_CONTEXT_CHARS:]
        if len(text_before_cursor) > BEAT_EXPAND_CONTEXT_CHARS
        else text_before_cursor
    )
    if recent.strip():
        parts.append(f"## 前文\n\n{recent}")
    if preceding_beats_prose.strip():
        parts.append(f"## 本轮已生成的内容\n\n{preceding_beats_prose}")
    parts.append(f"## 当前节拍（第 {beat_index + 1}/{total_beats} 拍）\n\n{beat}")
    append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)
