from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.projects import ConceptGenerateRequest
from app.schemas.prompt_profiles import GenerationProfile
from app.services.editor import PlanningEditorService


@pytest.mark.asyncio
async def test_generate_concepts_injects_selected_style_and_plot_profiles() -> None:
    llm_service = SimpleNamespace(
        invoke_completion=AsyncMock(
            return_value=(
                "### 纸上王朝\n"
                "寒门书生被迫冒名入局，以信息差换取第一份护身资源。\n"
            )
        )
    )
    provider_config_service = SimpleNamespace(
        ensure_enabled=AsyncMock(return_value=SimpleNamespace(id="provider-1"))
    )
    style_profile_service = SimpleNamespace(
        get_or_404=AsyncMock(
            return_value=SimpleNamespace(prompt_pack_payload="# Style Prompt\n冷白短句")
        )
    )
    plot_profile_service = SimpleNamespace(
        get_or_404=AsyncMock(
            return_value=SimpleNamespace(
                prompt_pack_payload=(
                    "# Plot Prompt\n"
                    "核心驱动轴：信息差胁迫 → 利益绑定 → 资源/能力兑现 → 关系重组 → 更高层次博弈。"
                )
            )
        )
    )
    service = PlanningEditorService(
        llm_service=llm_service,
        provider_config_service=provider_config_service,
        style_profile_service=style_profile_service,
        plot_profile_service=plot_profile_service,
    )

    result = await service.generate_concepts(
        session=object(),
        user_id="user-1",
        payload=ConceptGenerateRequest(
            inspiration="一个被迫冒名顶替入局的寒门书生。",
            provider_id="provider-1",
            count=1,
            generation_profile=GenerationProfile(
                genre_mother="xianxia",
                desire_overlays=["harem_collect"],
                intensity_level="explicit",
                pov_mode="limited_third",
                morality_axis="ruthless_growth",
                pace_density="fast",
            ),
            style_profile_id="style-1",
            plot_profile_id="plot-1",
        ),
    )

    assert result[0].title == "纸上王朝"
    style_profile_service.get_or_404.assert_awaited_once()
    plot_profile_service.get_or_404.assert_awaited_once()
    _, invoke_kwargs = llm_service.invoke_completion.await_args
    system_prompt = invoke_kwargs["system_prompt"]
    assert "# Style Prompt\n冷白短句" in system_prompt
    assert "# Plot Prompt\n核心驱动轴" in system_prompt
    assert "Plot 指纹落地契约" in system_prompt
    assert "概念生成阶段也必须应用已选 Plot/Style Profile" in system_prompt
    assert "genre_mother: xianxia" in system_prompt
    assert "desire_overlays: harem_collect" in system_prompt


@pytest.mark.asyncio
async def test_generate_concepts_keeps_profile_lookup_optional() -> None:
    llm_service = SimpleNamespace(
        invoke_completion=AsyncMock(
            return_value="### 无档案概念\n一段没有挂载档案时也能正常解析的简介。"
        )
    )
    provider_config_service = SimpleNamespace(
        ensure_enabled=AsyncMock(return_value=SimpleNamespace(id="provider-1"))
    )
    style_profile_service = SimpleNamespace(get_or_404=AsyncMock())
    plot_profile_service = SimpleNamespace(get_or_404=AsyncMock())
    service = PlanningEditorService(
        llm_service=llm_service,
        provider_config_service=provider_config_service,
        style_profile_service=style_profile_service,
        plot_profile_service=plot_profile_service,
    )

    result = await service.generate_concepts(
        session=object(),
        user_id="user-1",
        payload=ConceptGenerateRequest(
            inspiration="一个普通灵感。",
            provider_id="provider-1",
            count=1,
            generation_profile=GenerationProfile(
                genre_mother="urban",
                desire_overlays=[],
                intensity_level="edge",
                pov_mode="limited_third",
                morality_axis="gray_pragmatism",
                pace_density="balanced",
            ),
        ),
    )

    assert result[0].title == "无档案概念"
    style_profile_service.get_or_404.assert_not_awaited()
    plot_profile_service.get_or_404.assert_not_awaited()
