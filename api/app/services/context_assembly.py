"""上下文组装服务。

将风格母 Prompt 和故事圣经各区块组装为完整的 LLM 系统提示词。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.bible_fields import BIBLE_SECTION_ORDER
from app.core.length_presets import LengthPresetKey, get_progress


_WRITING_RULES = """

---

## 写作核心规则

### 叙事原则
- 展示不讲述（Show, Don't Tell）：用动作、对话、细节展现情感和性格
- 对话要有潜台词：每句对话应揭示角色性格或推动情节，禁止纯信息传递的水词
- 五感沉浸：每个新场景至少调用 2 种感官描写

### 节奏控制
- 保持快节奏：删除不必要的过渡和心理赘述
- 段落控制：单段不超过 150 字，适配移动端阅读
- 句式偏短：动作场景用短句加快节奏，情感场景可适当放长

### 禁止事项
- 不要以总结性语句开头（如「经过一番思考，他决定...」）
- 不要使用上帝视角泄露其他角色心理（除非叙事视角允许）
- 不要重复前文已述内容
- 直接续写正文，不要添加解释、前言或元评论
"""


@dataclass(frozen=True)
class WritingContextSections:
    inspiration: str = ""
    world_building: str = ""
    characters: str = ""
    outline_master: str = ""
    outline_detail: str = ""
    runtime_state: str = ""
    runtime_threads: str = ""


def assemble_writing_context(
    style_prompt: str,
    *,
    sections: WritingContextSections | None = None,
    length_preset: LengthPresetKey = "long",
    content_length: int = 0,
) -> str:
    """组装写作系统提示词：风格母Prompt + 各区块 + 写作规则 + 收束引导。"""
    resolved_sections = sections or WritingContextSections()
    values = {
        "inspiration": resolved_sections.inspiration,
        "world_building": resolved_sections.world_building,
        "characters": resolved_sections.characters,
        "outline_master": resolved_sections.outline_master,
        "outline_detail": resolved_sections.outline_detail,
        "runtime_state": resolved_sections.runtime_state,
        "runtime_threads": resolved_sections.runtime_threads,
    }

    parts = [style_prompt]

    sections: list[str] = []
    for label, key in BIBLE_SECTION_ORDER:
        text = values[key].strip()
        if text:
            sections.append(f"# {label}\n\n{text}")

    if sections:
        parts.append("\n\n---\n\n" + "\n\n".join(sections))

    parts.append(_WRITING_RULES)

    # 收束引导：根据进度 phase 追加提示
    if content_length > 0:
        progress = get_progress(content_length, length_preset)
        if progress["phase"] == "ending_zone":
            parts.append(
                f"\n\n## 收束引导\n\n"
                f"当前进度已达目标篇幅的 {progress['percentage']}%，"
                f"请开始引导故事走向结局：\n"
                f"- 不要开启新的情节线或引入新角色\n"
                f"- 开始回收已埋下的伏笔\n"
                f"- 情节向核心冲突的最终解决方向收束\n"
                f"- 节奏可以适当加快，推向高潮"
            )
        elif progress["phase"] == "over_target":
            parts.append(
                f"\n\n## 超出目标提醒\n\n"
                f"已超出目标篇幅上限（{progress['target_max']:,} 字），"
                f"请尽快收束故事：\n"
                f"- 必须在接下来的内容中完成结局\n"
                f"- 不要添加任何新元素\n"
                f"- 直接推进到最终结局"
            )

    return "\n".join(parts)
