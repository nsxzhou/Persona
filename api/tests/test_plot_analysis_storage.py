"""Unit tests for PlotAnalysisStorageService sketch artifact helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.plot_analysis_storage import PlotAnalysisStorageService


def _make_sketch(chunk_index: int, chunk_count: int = 3) -> dict:
    return {
        "chunk_index": chunk_index,
        "chunk_count": chunk_count,
        "characters_present": ["主角"],
        "events": [f"第 {chunk_index} 段的代表事件"],
        "advancement": "setup",
        "time_marker": "linear",
    }


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PERSONA_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_write_sketch_artifact_creates_file_and_exists_returns_true() -> None:
    service = PlotAnalysisStorageService()
    job_id = "job-write-exists"
    payload = _make_sketch(0)

    assert service.sketch_artifact_exists(job_id, 0) is False

    await service.write_sketch_artifact(job_id, 0, payload)

    assert service.sketch_artifact_exists(job_id, 0) is True
    sketch_path = service._sketch_artifact_path(job_id, 0)
    assert sketch_path.exists()
    # Non-ASCII Chinese characters must round-trip without escape.
    raw = sketch_path.read_text(encoding="utf-8")
    assert "主角" in raw
    assert json.loads(raw) == payload
    # Atomic write must not leave a .tmp sibling behind on success.
    assert list(sketch_path.parent.glob("*.tmp")) == []


@pytest.mark.asyncio
async def test_write_sketch_artifact_uses_zero_padded_six_digit_index() -> None:
    service = PlotAnalysisStorageService()
    job_id = "job-padding"

    await service.write_sketch_artifact(job_id, 7, _make_sketch(7))

    sketch_path = service._sketch_artifact_path(job_id, 7)
    assert sketch_path.name == "000007.json"
    assert sketch_path.parent.name == "sketches"


def test_count_sketch_artifacts_returns_zero_when_directory_missing() -> None:
    service = PlotAnalysisStorageService()
    assert service.count_sketch_artifacts("never-written-job") == 0


@pytest.mark.asyncio
async def test_count_sketch_artifacts_tracks_written_count() -> None:
    service = PlotAnalysisStorageService()
    job_id = "job-count"

    assert service.count_sketch_artifacts(job_id) == 0

    for index in range(3):
        await service.write_sketch_artifact(job_id, index, _make_sketch(index))

    assert service.count_sketch_artifacts(job_id) == 3
    # Atomic write must not leave .tmp siblings behind across multiple writes.
    sketch_dir = service._sketch_artifact_path(job_id, 0).parent
    assert list(sketch_dir.glob("*.tmp")) == []


@pytest.mark.asyncio
async def test_read_all_sketches_returns_sorted_by_chunk_index() -> None:
    service = PlotAnalysisStorageService()
    job_id = "job-sort"

    # Write out-of-order to prove sort behaviour is not just filesystem luck.
    for index in (4, 0, 2, 1, 3):
        await service.write_sketch_artifact(job_id, index, _make_sketch(index, chunk_count=5))

    sketches = await service.read_all_sketches(job_id)

    assert [item["chunk_index"] for item in sketches] == [0, 1, 2, 3, 4]
    # Payload contents are preserved verbatim.
    assert sketches[0] == _make_sketch(0, chunk_count=5)
    assert sketches[-1] == _make_sketch(4, chunk_count=5)


@pytest.mark.asyncio
async def test_read_all_sketches_returns_empty_list_when_directory_missing() -> None:
    service = PlotAnalysisStorageService()
    assert await service.read_all_sketches("never-written-job") == []


@pytest.mark.asyncio
async def test_read_sketch_batches_yields_expected_batch_sizes() -> None:
    service = PlotAnalysisStorageService()
    job_id = "job-batches"

    for index in range(5):
        await service.write_sketch_artifact(job_id, index, _make_sketch(index, chunk_count=5))

    batches = [
        batch
        async for batch in service.read_sketch_batches(job_id, batch_size=2)
    ]

    assert [[item["chunk_index"] for item in batch] for batch in batches] == [
        [0, 1],
        [2, 3],
        [4],
    ]


@pytest.mark.asyncio
async def test_read_sketch_batches_no_yield_when_directory_missing() -> None:
    service = PlotAnalysisStorageService()
    batches = [
        batch
        async for batch in service.read_sketch_batches("never-written-job", batch_size=2)
    ]
    assert batches == []
