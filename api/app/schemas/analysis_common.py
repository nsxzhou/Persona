from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class InputClassificationSchema(BaseModel):
    text_type: Literal["混合文本", "口语字幕", "章节正文"] = Field(
        description="Detected source text type.",
    )
    has_timestamps: bool = Field(default=False, description="Whether timestamp markers were detected.")
    has_speaker_labels: bool = Field(default=False, description="Whether speaker labels were detected.")
    has_noise_markers: bool = Field(default=False, description="Whether bracketed/noise markers were detected.")
    uses_batch_processing: bool = Field(default=False, description="Whether chunked batch analysis was used.")
    location_indexing: Literal["时间戳", "章节或段落位置", "无法定位"] = Field(
        default="无法定位",
        description="Evidence location indexing strategy.",
    )
    noise_notes: str = Field(
        default="未发现显著噪声。",
        description="Short note describing detected noise markers.",
    )
