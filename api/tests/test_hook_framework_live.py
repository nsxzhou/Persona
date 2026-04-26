from __future__ import annotations

import json
import tempfile
import textwrap
from pathlib import Path

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.live_llm


_DESCRIPTION = (
    "一个被富二代当众羞辱的普通职员，意外获得能看到他人把柄的神秘系统，"
    "从此在都市中步步逆袭，将曾经看不起他的人踩在脚下。"
)

_TEXT_BEFORE_CURSOR = (
    "林风推开酒店套房的门。沈雨霏站在落地窗前，一身香奈儿套装裹不住微微发抖的肩。"
    "这个曾经在董事会上当众罢免他的女总裁，此刻手里攥着他匿名寄来的那份财务报表。"
    "林风走过去，从背后贴近她耳边："
)

_BEAT = "林风在私密空间里用把柄胁迫沈雨霏，从权力臣服推进到身体占有与性征服"


async def _collect_sse_text(response) -> str:
    """Parse SSE stream and concatenate JSON-encoded chunks."""
    chunks: list[str] = []
    async for line in response.aiter_lines():
        line = line.strip()
        if line.startswith("data: "):
            payload = line[len("data: "):]
            try:
                decoded = json.loads(payload)
                if isinstance(decoded, str):
                    chunks.append(decoded)
            except json.JSONDecodeError:
                continue
        elif line.startswith("event: error"):
            raise RuntimeError(f"SSE error event received: {await response.aread()}")
    return "".join(chunks)


@pytest.mark.asyncio
async def test_hook_framework_live_outputs(
    initialized_live_client: AsyncClient,
    initialized_live_provider: dict[str, object],
    capsys,
) -> None:
    """Create two projects (mainstream vs nsfw) and stream expand-beat to compare raw prose output."""
    provider_id = str(initialized_live_provider["id"])

    profiles = {
        "mainstream": {
            "target_market": "mainstream",
            "genre_mother": "urban",
            "desire_overlays": [],
            "intensity_level": "plot_only",
            "pov_mode": "limited_third",
            "morality_axis": "gray_pragmatism",
            "pace_density": "balanced",
        },
        "nsfw_edge": {
            "target_market": "nsfw",
            "genre_mother": "urban",
            "desire_overlays": ["reverse_ntr"],
            "intensity_level": "edge",
            "pov_mode": "limited_third",
            "morality_axis": "domination_first",
            "pace_density": "fast",
        },
        "nsfw_explicit": {
            "target_market": "nsfw",
            "genre_mother": "urban",
            "desire_overlays": ["wife_steal"],
            "intensity_level": "explicit",
            "pov_mode": "deep_first",
            "morality_axis": "domination_first",
            "pace_density": "fast",
        },
        "nsfw_graphic": {
            "target_market": "nsfw",
            "genre_mother": "urban",
            "desire_overlays": ["wife_steal"],
            "intensity_level": "graphic",
            "pov_mode": "deep_first",
            "morality_axis": "domination_first",
            "pace_density": "fast",
        },
    }

    out_path = Path(tempfile.gettempdir()) / "hook_framework_outputs.md"
    lines: list[str] = []
    outputs: dict[str, str] = {}

    for label, profile in profiles.items():
        # 1. Create project
        create_resp = await initialized_live_client.post(
            "/api/v1/projects",
            json={
                "name": f"Hook Framework Live Test ({label})",
                "description": _DESCRIPTION,
                "status": "draft",
                "default_provider_id": provider_id,
                "default_model": "",
                "style_profile_id": None,
                "plot_profile_id": None,
                "generation_profile": profile,
                "length_preset": "short",
                "auto_sync_memory": False,
            },
        )
        assert create_resp.status_code == 201, f"Project creation failed for {label}: {create_resp.text}"
        project_id = create_resp.json()["id"]

        # 2. Stream expand-beat (正文展开)
        gen_resp = await initialized_live_client.post(
            f"/api/v1/projects/{project_id}/editor/expand-beat",
            json={
                "text_before_cursor": _TEXT_BEFORE_CURSOR,
                "beat": _BEAT,
                "beat_index": 1,
                "total_beats": 3,
            },
        )
        assert gen_resp.status_code == 200, f"Generation failed for {label}: {gen_resp.text}"

        text = await _collect_sse_text(gen_resp)
        assert text, f"Empty LLM output for {label}"
        outputs[label] = text

        # Append immediately so partial results survive later failures
        lines.append(f"\n{'=' * 80}")
        lines.append(f"# {label.upper()} MODE")
        lines.append(f"{'=' * 80}\n")
        lines.append(text)
        lines.append("")
        out_path.write_text("\n".join(lines), encoding="utf-8")

    # 3. Print all outputs for human inspection
    with capsys.disabled():
        for label, text in outputs.items():
            print()
            print("=" * 80)
            print(f"  OUTPUT: {label.upper()} MODE")
            print("=" * 80)
            print(textwrap.indent(text, "  "))
            print("=" * 80)
            print()
        print(f"\n[完整输出已写入: {out_path}]\n")
