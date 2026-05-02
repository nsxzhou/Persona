from __future__ import annotations

from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context
from app.prompts.novel_shared import (
    BEAT_GENERATE_CONTEXT_CHARS,
    MALE_COMMERCIAL_ENGINE,
    append_profile_blocks,
    get_hook_framework,
)
from app.schemas.prompt_profiles import GenerationProfile

_BEAT_GENERATE_SYSTEM_TEMPLATE = (
    "你是一位番茄金番作家，正在为接下来的正文安排场景节拍和情绪钩子。\n\n"
    f"{MALE_COMMERCIAL_ENGINE}"
    "节拍（Beat）是一个场景或情节的最小叙事单元，每条节拍用一句话概括将要发生的事。\n\n"
    "规划时用章节悬念节奏设计压住每一拍：\n"
    "- 每一拍都要服务本章悬念单元中的压力递进、兑现或认知颠覆\n"
    "- 关注伏笔三步法在本章内的埋设、强化或回收位置\n"
    "- 避免只有情绪标签，没有具体事件和读者奖励\n\n"
    "落笔规则：\n"
    "- 生成指定数量的节拍，每条节拍独占一行\n"
    "- 每行只写一条节拍本体，不要编号、不要项目符号、不要标题、不要代码块、不要前言和总结\n"
    "- 格式必须严格为：[情绪标签] 事件描述\n"
    "- 情绪标签只放在首个方括号中，正文紧跟其后，不要在正文里再补解释性标签\n"
    "  例：[平静→疑惑] 主角注意到地上有一串不属于任何人的脚印\n"
    "  例：[震惊→狂喜] 彻底打脸！\n"
    "- 节拍之间应有递进的叙事逻辑和情绪起伏\n"
    "- 在爽点兑现或欲望满足的高潮环节，允许连续的纯粹爽感、打脸或生理唤醒/肉体推倒的极致宣泄\n"
    "- 不要只写情绪变化，还要写清这一拍具体让读者追什么（如期待更深的堕落、更极致的打脸）\n"
    "- 动作可以是压制、夺回、极致打脸、关系突破、打破禁忌、彻底征服或堕落\n"
    "- 最后一拍必须是钩子（悬念/反转/新信息揭露），并且最后一拍要明确勾住下一拍最想看的兑现\n"
    "- 参考已有大纲和前文，保持情节连贯\n"
    "- 只输出节拍列表，不要解释、不要前言"
    "{hook_framework}"
)


def build_beat_generate_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    regenerating: bool = False,
) -> str:
    parts: list[str] = []
    append_profile_blocks(
        parts,
        style_prompt=style_prompt,
        plot_prompt=plot_prompt,
        plot_usage="用它规划压力递进、兑现节奏和章末推动点，不得替当前项目发明或照搬样本桥段。",
        generation_profile=generation_profile,
    )
    hook_framework = get_hook_framework(generation_profile)
    parts.append(_BEAT_GENERATE_SYSTEM_TEMPLATE.format(hook_framework=hook_framework))
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_beat_generate_user_message(
    text_before_cursor: str,
    outline_detail: str,
    runtime_state: str,
    runtime_threads: str,
    num_beats: int,
    length_context: str = "",
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
        text_before_cursor[-BEAT_GENERATE_CONTEXT_CHARS:]
        if len(text_before_cursor) > BEAT_GENERATE_CONTEXT_CHARS
        else text_before_cursor
    )
    if recent.strip():
        parts.append(f"## 前文（最近部分）\n\n{recent}")
    if length_context:
        parts.append(length_context)
    append_regeneration_context(parts, previous_output, user_feedback)
    parts.append(f"\n请生成 {num_beats} 个节拍：")
    return "\n\n---\n\n".join(parts)
