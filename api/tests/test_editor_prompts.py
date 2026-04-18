from __future__ import annotations

import pytest

from app.services.editor_prompts import (
    build_bible_update_system_prompt,
    build_bible_update_user_message,
    build_section_system_prompt,
    build_section_user_message,
)


def test_world_building_prompt_uses_core_scaffold_and_conditional_modules() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="long")

    assert "生成一份足以支撑人物、冲突和前期展开的必要设定" in prompt
    assert "若灵感未明确写出超自然，则默认不存在超自然" in prompt
    assert "只保留当前故事真正需要的模块" in prompt
    assert "1. **时代与秩序**" in prompt
    assert "2. **当前局势与核心冲突土壤**" in prompt
    assert "3. **主角当前处境与约束**" in prompt
    assert "仅在确有需要时，才补充下列可选模块" in prompt
    assert "特殊设定（仅灵感明示时）" in prompt
    assert "主要势力" in prompt
    assert "关键前史" in prompt
    assert "活动空间与扩展方向" in prompt
    assert "资源与利益流动" in prompt
    assert "隐秘规则/禁忌" not in prompt


def test_world_building_prompt_prefers_grounded_identity_swap_reading() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="long")

    assert "借皮囊/借壳/替身/换身份/李代桃僵" in prompt
    assert "默认优先按现实权谋或身份操作理解" in prompt
    assert "相貌相似、冒名顶替、伪造文书、家族关系运作、替考替身、身份植入" in prompt
    assert "不得把上述表达解释成世界规则、禁忌体系或异常机制" in prompt


def test_world_building_prompt_includes_grounded_and_supernatural_examples() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="medium")

    assert "示例（应按现实权谋理解）" in prompt
    assert "门阀夫人要借他皮囊一用" in prompt
    assert "应理解为身份顶替、冒名入局、关系运作或李代桃僵" in prompt
    assert "示例（才允许进入“特殊设定”）" in prompt
    assert "她需借尸还魂，必须在子时行夺舍仪式" in prompt
    assert "这类内容才允许扩写为超自然或异常机制" in prompt


@pytest.mark.parametrize("length_preset", ["short", "medium", "long"])
def test_world_building_prompt_removes_hard_coded_setting_checklist(
    length_preset: str,
) -> None:
    prompt = build_section_system_prompt("world_building", length_preset=length_preset)

    assert "必须覆盖以下六个维度" not in prompt
    assert "至少 3 个互相制衡的势力" not in prompt
    assert "至少 6 级" not in prompt
    assert "力量/修炼体系 3-4 级即可" not in prompt
    assert "力量体系 4-5 级，势力 2-3 个" not in prompt
    assert "经济必须与力量等级挂钩" not in prompt


def test_world_building_prompt_explicitly_blocks_over_generation() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="medium")

    assert "暧昧、诡秘、留白不等于存在隐藏机制" in prompt
    assert "历史、权谋、现实、悬疑等题材，不要默认生成公开修炼体系或全民力量系统" in prompt
    assert "历史、权谋、现实题材，不得因为灵感带有诡异感、暧昧感或留白，就自行补出秘密体系、禁忌机制或异常规则" in prompt
    assert "资源争夺并非主线时，不要专门发明货币、修炼材料、交易媒介" in prompt
    assert "不要为了显得完整而补完世界" in prompt
    assert "不要发明暂时不会进入剧情的设定" in prompt


def test_adjacent_prompts_preserve_grounded_reading() -> None:
    characters_prompt = build_section_system_prompt("characters", length_preset="long")
    outline_prompt = build_section_system_prompt("outline_master", length_preset="long")

    assert "沿用世界观已确定的题材解释，不得把现实权谋误写为超自然机制或秘密体系" in characters_prompt
    assert "沿用世界观已确定的题材解释，不得把现实权谋误写为超自然机制或秘密体系" in outline_prompt


def test_identity_swap_inspiration_regression_is_passed_with_grounded_guardrails() -> None:
    inspiration = (
        "好消息：穿成解元，才华横溢。坏消息：刚被诬下狱，择日问斩。"
        "绝境中，门阀望族的美艳夫人，要借我皮囊一用！"
    )

    user_message = build_section_user_message(
        "world_building",
        {
            "inspiration": inspiration,
            "world_building": "",
            "characters": "",
            "outline_master": "",
            "outline_detail": "",
            "runtime_state": "",
            "runtime_threads": "",
        },
    )
    system_prompt = build_section_system_prompt("world_building", length_preset="long")

    assert inspiration in user_message
    assert "借皮囊/借壳/替身/换身份/李代桃僵" in system_prompt
    assert "默认优先按现实权谋或身份操作理解" in system_prompt


def test_bible_update_prompt_uses_scope_aware_check_content_label() -> None:
    user_message = build_bible_update_user_message(
        current_runtime_state="旧状态",
        current_runtime_threads="旧伏笔",
        content_to_check="这是整章正文",
        sync_scope="chapter_full",
    )

    assert "## 当前运行时状态\n\n旧状态" in user_message
    assert "## 当前伏笔与线索追踪\n\n旧伏笔" in user_message
    assert "## 待检查正文（整章）\n\n这是整章正文" in user_message
    assert "## 本次新生成的正文" not in user_message


def test_bible_update_system_prompt_forbids_placeholder_references() -> None:
    system_prompt = build_bible_update_system_prompt()

    assert "输出两个区块的完整最终版本（可直接替换旧文档）" in system_prompt
    assert "严禁使用“保留原有/同上/沿用旧内容/并追加以下/其余不变”等指代或占位语" in system_prompt
    assert "新增事件、角色、伏笔必须与旧信息合并后完整输出，不能只输出增量" in system_prompt
    assert "- 保留原有内容中仍然有效的信息" not in system_prompt


def test_bible_update_system_prompt_prefers_minimal_persistent_memory() -> None:
    system_prompt = build_bible_update_system_prompt()

    assert "只保留会影响后续章节的持续性变化" in system_prompt
    assert "稳定事实变化" in system_prompt
    assert "关系变化" in system_prompt
    assert "未回收线索或新风险" in system_prompt
    assert "优先判断是否无需更新" in system_prompt
    assert "不要把本章剧情改写成摘要" in system_prompt
