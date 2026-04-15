"""上下文组装服务。

将风格母 Prompt 和故事圣经各区块组装为完整的 LLM 系统提示词。
"""

from __future__ import annotations

from app.core.bible_fields import BIBLE_SECTION_ORDER


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


def assemble_writing_context(
    style_prompt: str,
    *,
    inspiration: str = "",
    world_building: str = "",
    characters: str = "",
    outline_master: str = "",
    outline_detail: str = "",
    story_bible: str = "",
) -> str:
    """组装写作系统提示词：风格母Prompt + 故事圣经各区块 + 写作规则。"""
    values = {
        "inspiration": inspiration,
        "world_building": world_building,
        "characters": characters,
        "outline_master": outline_master,
        "outline_detail": outline_detail,
        "story_bible": story_bible,
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

    return "\n".join(parts)
