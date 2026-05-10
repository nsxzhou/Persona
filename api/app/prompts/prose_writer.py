from __future__ import annotations

from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context
from app.prompts.novel_shared import (
    BEAT_EXPAND_CONTEXT_CHARS,
    build_desire_semantics_hint,
    build_plot_propulsion_contract,
    append_profile_blocks,
    get_commercial_engine,
    get_hook_framework,
)
from app.schemas.prompt_profiles import GenerationProfile


VOICE_PROFILE_LANGUAGE_PRIORITY_CONTRACT = """
# Voice Profile Runtime Contract（语言层最高优先级）

- 已挂载 Voice Profile 时，它是整章正文写作的语言层最高优先级。
- 本章正文必须优先执行 Voice Profile 中的句式、词汇、对白、标点、节奏、意象、叙述视角和写作忌口。
- 商业爽点、节拍推进和 Generation Profile 仍要完成，但落笔方式要先服从 Voice Profile 的语言指纹。
- 冲突边界：Voice Profile 只约束语言表达，不覆盖当前项目事实、角色关系、世界观、剧情走向、题材强度和边界规则。
- 不得复制样本角色、设定、事件或桥段；样本专名和专属设定只能抽象成语气、节奏或叙述手法。
""".strip()


def _build_chapter_expand_system(
    hook_framework: str = "",
    commercial_engine: str = "",
) -> str:
    return (
        "你是一位番茄金番作家，正在根据完整节拍列表一次性写出本章正文。\n\n"
        f"{commercial_engine}"
        f"{build_plot_propulsion_contract()}\n"
        "全章落笔规则：\n"
        "- 节拍列表是剧情骨架，不是正文篇幅上限；每条节拍都要扩写成完整可读的场景推进、感官落点、对白博弈、心理反应和读者奖励\n"
        "- 可以围绕节拍做充分的创造性展开，但必须按节拍列表原顺序覆盖全部节拍，不得跳拍、并拍、重排或额外改写节拍目标\n"
        "- 目标篇幅为 3000-5000 个中文字符，并把篇幅均匀分配到各个节拍；8 个节拍时每拍大约展开 350-600 个中文字符，节拍更少时每拍要扩写得更充分\n"
        "- 输出只能是读者可见的小说正文\n"
        "- 禁止输出章节标题、小标题、节拍编号、节拍标签、列表、分析说明、代码围栏、前言或结语\n"
        "- 保持与前文的语感和风格一致，自然衔接前文，不要重复已有内容\n"
        "- 段落控制在 150 字以内，适配移动端阅读\n"
        "- 对话要有潜台词，动作/战斗场景用短句加快节奏\n"
        "- 每一组段落都要落下可感知的读者奖励，如局势推进、资源兑现、权力变化、关系张力或信息差反转\n"
        "- 结尾必须形成章末钩子，让读者明确期待下一章的冲突、反转或兑现\n"
        f"{hook_framework}"
    )


def build_chapter_expand_system_prompt(
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
        plot_usage="写作时只用于防止情节跑偏和洗白，不得复制样本角色、设定、事件或桥段。",
        generation_profile=generation_profile,
    )
    if style_prompt:
        parts.append(VOICE_PROFILE_LANGUAGE_PRIORITY_CONTRACT)
        parts.append("\n\n---\n")
    hook_framework = get_hook_framework(generation_profile) + build_desire_semantics_hint(generation_profile)
    parts.append(
        _build_chapter_expand_system(
            hook_framework,
            get_commercial_engine(generation_profile),
        )
    )
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_chapter_expand_user_message(
    *,
    text_before_cursor: str,
    beats: list[str],
    outline_detail: str,
    runtime_state: str,
    runtime_threads: str,
    current_chapter_context: str = "",
    previous_chapter_context: str = "",
    active_character_focus: str = "",
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    parts: list[str] = []
    if current_chapter_context.strip():
        parts.append(f"## 当前章节\n\n{current_chapter_context}")
    if active_character_focus.strip():
        parts.append(f"# Active Character Focus\n\n{active_character_focus}")
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
    beat_lines = "\n".join(f"{index + 1}. {beat}" for index, beat in enumerate(beats))
    parts.append(
        "## 完整节拍列表（必须按顺序覆盖）\n\n"
        f"{beat_lines}\n\n"
        "硬锁：当前章节上下文中的本章核心事件和章末钩子必须保留；"
        "完整节拍列表必须按原顺序逐拍抵达，不得跳拍、并拍或重排。\n\n"
        "节拍只是剧情骨架，不是正文篇幅上限。可以围绕每拍充分扩写场景推进、"
        "对白博弈、心理反应、细节承压和读者奖励，但扩写后仍要回到对应节拍的剧情落点。\n\n"
        "篇幅规则：目标 3000-5000 个中文字符，并把篇幅分配到全部节拍；"
        "8 个节拍时每拍大约 350-600 个中文字符，节拍更少时每拍要扩写得更充分。\n\n"
        "语言层执行提醒：全章正文必须沿用已挂载 Voice Profile 的语言指纹，"
        "优先落实句式、词汇、对白、标点、节奏、意象和写作忌口。\n\n"
        "请一次性输出 3000-5000 个中文字符的完整章节正文。只输出正文。"
    )
    append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)


def build_chapter_expand_review_system_prompt() -> str:
    return (
        "你是一位连载章节质量审校人，只负责指出本章生成稿的交付风险。\n"
        "检查维度：节拍覆盖与顺序、3000-5000 中文字符目标、结构漂移、禁用格式噪音、章末钩子质量。\n"
        "只输出 JSON 对象，不要 Markdown，不要代码围栏。格式必须为：\n"
        '{"issues":["问题1","问题2"]}\n'
        "如果没有问题，输出 {\"issues\":[]}。"
    )


def build_chapter_expand_review_user_message(
    *,
    beats: list[str],
    prose_markdown: str,
) -> str:
    beat_lines = "\n".join(f"{index + 1}. {beat}" for index, beat in enumerate(beats))
    return (
        "## 完整节拍列表\n\n"
        f"{beat_lines}\n\n"
        "---\n\n"
        "## 待审校正文\n\n"
        f"{prose_markdown}"
    )
