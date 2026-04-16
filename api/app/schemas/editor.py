from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.projects import ConceptGenerateRequest, ConceptGenerateResponse


class EditorCompletionRequest(BaseModel):
    text_before_cursor: str
    current_chapter_context: str = ""
    previous_chapter_context: str = ""
    total_content_length: int = Field(default=0, ge=0)


class SectionGenerateRequest(BaseModel):
    section: str = Field(description="要生成的区块名称")
    inspiration: str = ""
    world_building: str = ""
    characters: str = ""
    outline_master: str = ""
    outline_detail: str = ""
    runtime_state: str = ""
    runtime_threads: str = ""


class BibleUpdateRequest(BaseModel):
    current_runtime_state: str = ""
    current_runtime_threads: str = ""
    new_content_context: str = Field(description="本次新生成的文本")


class BibleUpdateResponse(BaseModel):
    proposed_runtime_state: str
    proposed_runtime_threads: str


class BeatGenerateRequest(BaseModel):
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


class BeatExpandRequest(BaseModel):
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


class VolumeChaptersRequest(BaseModel):
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
]
