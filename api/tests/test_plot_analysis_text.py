from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from app.services.plot_analysis_text import read_plot_chunks_and_classification


async def _stream_text(text: str) -> AsyncIterator[bytes]:
    yield text.encode("utf-8")


def _repeat(label: str, count: int) -> str:
    return (label * count).strip()


@pytest.mark.asyncio
async def test_plot_chunking_prefers_chapter_and_scene_boundaries() -> None:
    scene_a = _repeat("甲场景推进。", 720)
    scene_b = _repeat("乙场景冲突。", 720)
    scene_c = _repeat("丙场景收束。", 720)
    emitted_chunks: list[tuple[int, str]] = []

    async def on_chunk(index: int, chunk_text: str) -> None:
        emitted_chunks.append((index, chunk_text))

    text = (
        "第一章 初入宗门\n\n"
        f"{scene_a}\n\n"
        "***\n\n"
        "子场景：演武场\n\n"
        f"{scene_b}\n\n"
        "第二章 余波\n\n"
        f"{scene_c}"
    )

    chunk_count, _character_count, classification, manifest = await read_plot_chunks_and_classification(
        _stream_text(text),
        on_chunk=on_chunk,
    )

    assert chunk_count == 3
    assert classification["location_indexing"] == "章节或段落位置"
    assert [entry["index"] for entry in manifest] == [0, 1, 2]
    assert "第一章 初入宗门" in emitted_chunks[0][1]
    assert "***" in emitted_chunks[1][1]
    assert "第二章 余波" in emitted_chunks[2][1]


@pytest.mark.asyncio
async def test_plot_chunking_uses_boundary_detector_for_oversized_continuous_block() -> None:
    paragraphs = [
        _repeat(f"第{i}段连续叙事。", 520) for i in range(1, 6)
    ]
    calls: list[list[str]] = []

    async def boundary_detector(block_paragraphs: list[str]) -> list[int] | None:
        calls.append(block_paragraphs)
        return [3]

    emitted_chunks: list[str] = []

    async def on_chunk(index: int, chunk_text: str) -> None:
        del index
        emitted_chunks.append(chunk_text)

    text = "\n\n".join(paragraphs)

    chunk_count, _character_count, _classification, _manifest = await read_plot_chunks_and_classification(
        _stream_text(text),
        on_chunk=on_chunk,
        boundary_detector=boundary_detector,
    )

    assert chunk_count == 2
    assert len(calls) == 1
    assert calls[0] == paragraphs
    assert "第1段连续叙事" in emitted_chunks[0]
    assert "第4段连续叙事" in emitted_chunks[1]


@pytest.mark.asyncio
async def test_plot_chunking_falls_back_when_boundary_detector_returns_invalid_indexes() -> None:
    paragraphs = [
        _repeat(f"第{i}段普通正文。", 520) for i in range(1, 6)
    ]

    async def boundary_detector(_block_paragraphs: list[str]) -> list[int] | None:
        return [99]

    emitted_chunks: list[str] = []

    async def on_chunk(index: int, chunk_text: str) -> None:
        del index
        emitted_chunks.append(chunk_text)

    text = "\n\n".join(paragraphs)

    chunk_count, _character_count, _classification, manifest = await read_plot_chunks_and_classification(
        _stream_text(text),
        on_chunk=on_chunk,
        boundary_detector=boundary_detector,
    )

    assert chunk_count == 2
    assert len(manifest) == 2
    assert "第1段普通正文" in emitted_chunks[0]
    assert "第5段普通正文" in emitted_chunks[1]
