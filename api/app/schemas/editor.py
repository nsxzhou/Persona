from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.projects import ConceptGenerateRequest, ConceptGenerateResponse
from app.schemas.prompt_profiles import GenerationProfile

MemorySyncScope = Literal["generated_fragment", "chapter_full"]


class _RegenerationFields(BaseModel):
    """Shared optional regeneration fields for "regenerate with optional feedback"."""

    previous_output: str | None = Field(
        default=None,
        description="上一版生成结果（前端从当前稿或缓存中取），用于旧稿修订式重生成",
    )
    user_feedback: str | None = Field(
        default=None,
        description="用户本次对生成的意见/期望（可选），会作为高优先级要求写入 prompt",
    )


class EditorCompletionRequest(BaseModel):
    text_before_cursor: str
    current_chapter_context: str = ""
    previous_chapter_context: str = ""
    total_content_length: int = Field(default=0, ge=0)
    generation_profile: GenerationProfile | None = None


class SectionGenerateRequest(_RegenerationFields):
    section: str = Field(description="要生成的区块名称")
    description: str = ""
    world_building: str = ""
    characters_blueprint: str = ""
    outline_master: str = ""
    outline_detail: str = ""
    characters_status: str = ""
    runtime_state: str = ""
    runtime_threads: str = ""


class BibleUpdateRequest(_RegenerationFields):
    current_characters_status: str = ""
    current_runtime_state: str = ""
    current_runtime_threads: str = ""
    content_to_check: str = Field(description="待检查的正文内容")
    sync_scope: MemorySyncScope = Field(description="本次检查的正文范围")


class BibleUpdateResponse(BaseModel):
    proposed_characters_status: str
    proposed_runtime_state: str
    proposed_runtime_threads: str
    proposed_summary: str | None = None
    changed: bool


class BeatGenerateRequest(_RegenerationFields):
    text_before_cursor: str
    runtime_state: str = ""
    runtime_threads: str = ""
    outline_detail: str = ""
    num_beats: int = Field(default=8, ge=3, le=15)
    current_chapter_context: str = Field(default="", description="当前章节的结构化上下文")
    previous_chapter_context: str = Field(default="", description="前序章节上下文")
    total_content_length: int = Field(default=0, ge=0)


class BeatGenerateResponse(BaseModel):
    beats: list[str]


class BeatExpandRequest(_RegenerationFields):
    text_before_cursor: str
    runtime_state: str = ""
    runtime_threads: str = ""
    outline_detail: str = ""
    beat: str
    beat_index: int
    total_beats: int
    preceding_beats_prose: str = ""
    current_chapter_context: str = Field(default="", description="当前章节的结构化上下文")
    previous_chapter_context: str = Field(default="", description="前序章节上下文")


class VolumeGenerateRequest(_RegenerationFields):
    """Payload for volume structure generation (only used for regeneration)."""


class VolumeChaptersRequest(_RegenerationFields):
    volume_index: int = Field(ge=0, description="要生成章节的卷索引（0-based）")


__all__ = [
    "BeatExpandRequest",
    "BeatGenerateRequest",
    "BeatGenerateResponse",
    "BibleUpdateRequest",
    "BibleUpdateResponse",
    "ConceptGenerateRequest",
    "ConceptGenerateResponse",
    "EditorCompletionRequest",
    "SectionGenerateRequest",
    "VolumeChaptersRequest",
    "VolumeGenerateRequest",
]
