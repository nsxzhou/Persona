from __future__ import annotations

from app.core.length_presets import LengthPresetKey
from app.prompts.common import REGENERATION_GUIDANCE
from app.prompts.novel_shared import (
    append_profile_blocks,
    build_direct_output_rules,
)
from app.prompts.section_context import build_section_user_message
from app.schemas.prompt_profiles import GenerationProfile

_WORLD_BUILDING_INSTRUCTION_TEMPLATE = (
    "从简介和已有上下文里抽出足以支撑人物、冲突和前期展开的必要设定，产出纯内部创作 Bible，不写读者可见正文。\n\n"
    "落笔前先做隐式判断，不要把判断过程写出来：\n"
    "1. 先判断这部作品更接近哪种题材；"
    "2. 再判断哪些设定模块对当前故事真正必要；"
    "3. 若简介未明确写出超自然，则默认不存在超自然；"
    "4. 只保留当前故事真正需要的模块，只生成当前故事真正需要的模块，不追求完美。\n\n"
    "世界观不是资料库，而是故事运行底层。核心设定必须至少影响一项故事功能：角色选择、冲突升级、信息差、资源流动或行动成本。\n\n"
    "用三维世界构建法做隐式质检，但不要输出成固定结构：物理维度、社会维度、隐喻维度都要服务角色冲突，且至少留下一条会影响角色选择的断层线。\n\n"
    "固定输出以下六个核心区块，二级标题必须逐字使用：\n"
    "## 世界底盘\n"
    "## 秩序与压力\n"
    "## 资源与利益\n"
    "## 规则漏洞\n"
    "## 前期可用冲突\n"
    "## 禁止补完\n\n"
    "区块写法：\n"
    "- 每个必需区块通常写 2-5 条；每条 1-3 句\n"
    "- 可在区块内增加贴合题材的小标题，但只在简介或上下文支持时出现\n"
    "- 避免长篇历史散文、百科式术语表、完整势力年表和暂时不会进入剧情的设定\n"
    "- 不要把三维世界构建法写成输出目录，只把它当作检查设定是否立得住的内部标准\n\n"
    "收束规则：\n"
    "- 历史、权谋、现实、悬疑等题材，不要默认生成公开修炼体系或全民力量系统\n"
    "- 资源争夺并非主线时，不要专门发明货币、修炼材料、交易媒介\n"
    "- 不要为了显得完整而补完世界\n"
    "- 不要发明暂时不会进入剧情的设定\n"
)


def _format_world_building_generation_profile(
    generation_profile: GenerationProfile | None,
) -> str:
    if generation_profile is None:
        return ""
    lines = [
        "# Generation Profile（世界观资产约束）",
        "",
        f"target_market: {generation_profile.target_market}",
        f"genre_mother: {generation_profile.genre_mother}",
    ]
    if generation_profile.target_market == "nsfw":
        lines.extend(
            [
                f"desire_overlays: {', '.join(generation_profile.desire_overlays)}",
                f"intensity_level: {generation_profile.intensity_level}",
            ]
        )
    lines.extend(
        [
            f"morality_axis: {generation_profile.morality_axis}",
            f"pace_density: {generation_profile.pace_density}",
            "",
            "这些字段只用于校准题材边界、压力强度和推进密度，不添加正文视角或叙事口吻规则。",
        ]
    )
    return "\n".join(lines)


def build_world_building_system_prompt(
    style_prompt: str | None = None,
    plot_prompt: str | None = None,
    generation_profile: GenerationProfile | None = None,
    length_preset: LengthPresetKey = "long",
    regenerating: bool = False,
) -> str:
    parts: list[str] = []
    append_profile_blocks(
        parts,
        style_prompt=None,
        plot_prompt=plot_prompt,
        plot_usage="只吸收压力系统、推进节奏、角色功能位和兑现逻辑，不得照搬样本角色、设定、事件。",
        generation_profile=None,
    )
    generation_profile_block = _format_world_building_generation_profile(generation_profile)
    if generation_profile_block:
        parts.append(generation_profile_block)
        parts.append("\n\n---\n")
    parts.append(
        "你是一位起点白金作家，正在为自己的新书整理可供后续角色、总纲、章节调用的「世界观设定」。\n"
        f"{_WORLD_BUILDING_INSTRUCTION_TEMPLATE}\n\n"
        f"{build_direct_output_rules()}"
    )
    if regenerating:
        parts.append(REGENERATION_GUIDANCE)
    return "\n".join(parts)


def build_world_building_user_message(
    context: dict[str, str],
    previous_output: str | None = None,
    user_feedback: str | None = None,
) -> str:
    return build_section_user_message(
        "world_building",
        context,
        previous_output=previous_output,
        user_feedback=user_feedback,
    )
