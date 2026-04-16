from __future__ import annotations

import pytest

from app.services.editor_prompts import build_section_system_prompt


def test_world_building_prompt_uses_core_scaffold_and_conditional_modules() -> None:
    prompt = build_section_system_prompt("world_building", length_preset="long")

    assert "生成一份足以支撑人物、冲突和前期展开的必要设定" in prompt
    assert "先判断这部作品更接近哪种题材气质，以及超自然设定是显性、隐性还是不存在" in prompt
    assert "只保留当前故事真正需要的模块" in prompt
    assert "1. **时代与秩序**" in prompt
    assert "2. **当前局势与核心冲突土壤**" in prompt
    assert "3. **主角受限规则**" in prompt
    assert "仅在确有需要时，才补充下列可选模块" in prompt
    assert "隐秘规则/禁忌" in prompt
    assert "主要势力" in prompt
    assert "关键前史" in prompt
    assert "活动空间与扩展方向" in prompt
    assert "资源与利益流动" in prompt


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

    assert "历史、权谋、现实、悬疑等题材，不要默认生成公开修炼体系或全民力量系统" in prompt
    assert "资源争夺并非主线时，不要专门发明货币、修炼材料、交易媒介" in prompt
    assert "少数人掌握的异常规则，不要包装成全民通用系统" in prompt
    assert "不要为了显得完整而补完世界" in prompt
    assert "不要发明暂时不会进入剧情的设定" in prompt
