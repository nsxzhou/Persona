from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.services.style_analysis_pipeline import StyleAnalysisPipeline


@pytest.mark.asyncio
async def test_style_pipeline_sets_postprocessing_stage_for_voice_profile(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    seen_stages: list[str | None] = []

    class FakeClient:
        def build_model(self, *, provider: object, model_name: str) -> object:
            return SimpleNamespace(provider=provider, model_name=model_name)

        async def ainvoke_markdown(
            self,
            *,
            model: object,
            prompt: str,
            provider: object | None = None,
            model_name: str | None = None,
            injection_task: object | None = None,
        ) -> str:
            del model, provider, model_name, injection_task
            if "生成一个可复用的 Voice Profile" in prompt:
                return (
                    "# Voice Profile\n"
                    "## sentence_rhythm\n- 短句推进\n\n"
                    "## narrative_distance\n- 贴近主角\n\n"
                    "## detail_anchors\n- 呼吸\n\n"
                    "## dialogue_aggression\n- 试探\n\n"
                    "## irregularity_budget\n- 轻微断裂\n\n"
                    "## anti_ai_guardrails\n- 禁止解释腔\n"
                )
            raise AssertionError(f"unexpected prompt: {prompt[:80]}")

    pipeline = StyleAnalysisPipeline(
        provider=SimpleNamespace(base_url="https://api.example.test/v1", api_key_encrypted="encrypted"),
        model_name="gpt-4.1-mini",
        style_name="古龙风格实验",
        source_filename="sample.txt",
        llm_client=FakeClient(),
        stage_callback=lambda stage: seen_stages.append(stage) or asyncio.sleep(0),
    )

    state = {
        "job_id": "job-style-post",
        "style_name": "古龙风格实验",
        "source_filename": "sample.txt",
        "model_name": "gpt-4.1-mini",
        "chunk_count": 2,
        "classification": {
            "text_type": "章节正文",
            "has_timestamps": False,
            "has_speaker_labels": False,
            "has_noise_markers": False,
            "uses_batch_processing": True,
            "location_indexing": "章节或段落位置",
            "noise_notes": "未发现显著噪声。",
        },
        "analysis_report_markdown": "# 执行摘要\n报告\n",
    }

    voice_profile_result = await pipeline._build_voice_profile(state)  # noqa: SLF001

    assert voice_profile_result["voice_profile_markdown"].startswith("# Voice Profile")
    assert "sentence_rhythm" in voice_profile_result["voice_profile_markdown"]
    assert seen_stages == ["postprocessing"]
    get_settings.cache_clear()
