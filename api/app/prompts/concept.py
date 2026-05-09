from __future__ import annotations

import re

from pydantic import BaseModel

from app.core.domain_errors import UnprocessableEntityError
from app.prompts.common import REGENERATION_GUIDANCE, append_regeneration_context
from app.prompts.novel_shared import build_direct_output_rules
from app.schemas.prompt_profiles import GenerationProfile


class ConceptCard(BaseModel):
    title: str
    synopsis: str


def parse_concept_response(raw: str, expected_count: int) -> list[ConceptCard]:
    text = raw.strip()
    concepts: list[ConceptCard] = []
    for part in re.split(r"^###\s+", text, flags=re.MULTILINE):
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        if len(lines) < 2:
            continue
        title = re.sub(r"^\d+[\.、\s]+", "", lines[0].strip())
        synopsis = lines[1].strip()
        if title and synopsis:
            concepts.append(ConceptCard(title=title, synopsis=synopsis))
    if not concepts:
        raise UnprocessableEntityError("AI 返回的格式无法解析，请重试")
    return concepts[:expected_count]


_CONCEPT_GENERATE_SYSTEM_TEMPLATE = (
    "你是一位深耕网文市场（起点、番茄等平台）的资深策划编辑，判断标准是读者会不会点、会不会追、会不会等更新。\n\n"
    "你需要根据用户给出的灵感描述，先判断最有点击力的故事承诺，再产出指定数量的小说概念卡。"
    "这里的概念卡是读者会看到的书页包装，不是创作规划书、设定表或投流分析。"
    "内部判断只服务于抓住第一眼卖点，不需要把规划公式填满。"
    "这些概念卡必须共享同一故事主轴，是同一本书的不同包装方向，"
    "不能写成三本完全不同的小说。"
    "每个概念包含标题和一段可直接放到书页上的简介。\n\n"
    "## 市场判断标准\n"
    "- 第一眼能看懂主角是谁、被什么局面逼住，或这个世界/机制哪里异常\n"
    "- 卖点必须落在具体的人、局、机制、冲突、选择或问题上，不用内部术语替读者做分析\n"
    "- 读完简介后，读者应该自然想知道下一步会发生什么，而不是只觉得设定很完整\n\n"
    "## 生成前的隐式判断\n"
    "在输出前，先在内部完成以下判断，但不要把判断过程写出来：\n"
    "- 主角是谁，当前最抓人的身份和处境是什么\n"
    "- 读者为什么会点进来并继续追，这本书当前最强的故事承诺是什么\n"
    "- 真正能支撑点击的核心卖点是什么\n"
    "- 显性冲突、潜在危机、主角核心驱动力是否指向同一个故事承诺\n"
    "- 简介是否适合用短标签、对白、问题、碎片句、世界异常、身份压力或机制开头\n\n"
    "## 差异化规则\n"
    "所有概念卡都必须保留同一故事主轴，只能改变卖点切口与包装方式。\n"
    "差异优先体现在主角切口、局势压力、关系张力、破局手段或兑现方式。\n"
    "可变化的入口包括：身份压力、世界异常、机制玩法、关系张力、对抗局面、资源问题或悬念问题。\n"
    "不要为了拉开差异，硬把同一主轴写成更大的体系、更多的势力或更高的世界层级。\n"
    "概念卡之间要像同一本书的不同书页包装方向，不是只换标题和设定表皮。\n\n"
    "## 标题规则\n"
    "- 标题要符合现代网文命名气质，可以短狠、反问、反差、轻俏，但不要冗长解释\n"
    "- 禁止平庸标题如「我的XXX之旅」「关于XXX这件事」\n"
    "- 标题要让题材、身份压力、反差关系或核心机制至少有一个能被读者立刻感知\n\n"
    "## 简介规则\n"
    "- 使用真实书页简介的形态：可以是一段短钩子，也可以是 1-3 个自然段；强钩子允许更短\n"
    "- 开头可以是对白、问题、碎片句、世界异常、身份压力、机制亮点或直接叙事，不必统一成项目说明\n"
    "- 短标签可选；只有用户灵感里已经有对应卖点时才使用，不要为了网文味硬加系统、多女主、修罗场等标签\n"
    "- 尽快让读者看见具体的人、局、机制、冲突或选择；不要先铺抽象背景\n"
    "- 结尾可以留问题、反压、未兑现承诺或下一步局势，但不要写成广告标语或硬拗金句\n\n"
    "## 写法要求\n"
    "- 像小说简介，不像广告投流文案\n"
    "- 先写人和局，再写大词，不要空泛开场\n"
    "- 可以有网文味和爽点，但不要油腻、不要连续宣传腔\n"
    "- 不要连续堆砌模板反转句、排比句、四字词和宣言句\n"
    "- 不要把简介写成金句合集\n"
    "- 不要为了显得炸裂而生造宏大名词、尊号和设定术语\n"
    "- 标签如果使用，只能压缩卖点，不能替代正文\n\n"
    "## 输出格式\n"
    "请使用 Markdown 格式输出，每个概念采用以下结构：\n"
    "### [标题]\n"
    "[简介]\n\n"
    f"{build_direct_output_rules(extra_rules=('直接输出内容，不要添加任何其他前言或总结、也不要输出任何序号、分析字段、DNA字段或解释说明。',))}"
)


def _format_concept_plot_prompt_pack(plot_prompt: str) -> str:
    return (
        "# Plot Prompt Pack（情节结构参考）\n\n"
        f"{plot_prompt.strip()}\n\n"
        "使用方式：Plot Pack 在概念生成阶段只作为结构参考，用来理解故事承诺、压力形态和兑现节奏；"
        "它不是标题或简介的内容模板，也不是需要显性复述的分析框架。"
        "标题和简介必须写成读者可见的书页包装，不要输出主驱动轴、读者追读问题、角色功能位等分析术语或模板字段。"
    )


def build_concept_generate_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    regenerating: bool = False,
) -> str:
    parts: list[str] = []
    if plot_prompt:
        parts.append(_format_concept_plot_prompt_pack(plot_prompt))
        parts.append("\n\n---\n")
    parts.append(_CONCEPT_GENERATE_SYSTEM_TEMPLATE)
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_concept_generate_user_message(
    inspiration: str,
    count: int,
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    parts: list[str] = [f"灵感输入，产出 {count} 个小说概念：\n\n{inspiration}"]
    append_regeneration_context(parts, previous_output, user_feedback)
    return "\n\n---\n\n".join(parts)
