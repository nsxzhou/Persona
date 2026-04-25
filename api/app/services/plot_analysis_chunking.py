from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlotChunkContext:
    primary_text: str
    overlap_before: str = ""
    overlap_after: str = ""
