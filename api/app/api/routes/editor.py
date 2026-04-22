"""Editor AI endpoints — thin handlers delegating to EditorService sub-services."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import (
    CurrentUserDep,
    DbSessionDep,
    EditorServiceDep,
)
from app.api.sse import sse_response
from app.schemas.editor import (
    BeatExpandRequest,
    BeatGenerateRequest,
    BeatGenerateResponse,
    BibleUpdateRequest,
    BibleUpdateResponse,
    ConceptGenerateRequest,
    ConceptGenerateResponse,
    EditorCompletionRequest,
    SectionGenerateRequest,
    VolumeChaptersRequest,
    VolumeGenerateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["editor"],
)


@router.post("/generate-concepts", response_model=ConceptGenerateResponse)
async def generate_concepts(
    payload: ConceptGenerateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> ConceptGenerateResponse:
    """Generate concept candidates for a new project."""
    concepts = await editor_service.planning.generate_concepts(
        db_session, current_user.id, payload,
    )
    return ConceptGenerateResponse(concepts=concepts)


@router.post("/{project_id}/editor/complete")
async def editor_complete(
    project_id: str,
    payload: EditorCompletionRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> StreamingResponse:
    """Stream continuation text for the active project editor session."""
    gen = await editor_service.writing.stream_completion(
        db_session, project_id, current_user.id, payload,
    )
    return sse_response(gen, error_log_message="AI 续写异常")


@router.post("/{project_id}/editor/generate-section")
async def generate_section(
    project_id: str,
    payload: SectionGenerateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> StreamingResponse:
    """Stream generated bible content for a single planning section."""
    gen = await editor_service.writing.stream_section_generation(
        db_session, project_id, current_user.id, payload,
    )
    return sse_response(gen, error_log_message="区块 AI 生成异常")


@router.post(
    "/{project_id}/editor/propose-bible-update",
    response_model=BibleUpdateResponse,
)
async def propose_bible_update(
    project_id: str,
    payload: BibleUpdateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> BibleUpdateResponse:
    """Propose runtime-state and thread updates from newly written content."""
    proposed_state, proposed_threads, changed = await editor_service.memory.propose_bible_update(
        db_session, project_id, current_user.id, payload,
    )
    return BibleUpdateResponse(
        proposed_runtime_state=proposed_state,
        proposed_runtime_threads=proposed_threads,
        changed=changed,
    )


@router.post(
    "/{project_id}/editor/generate-beats",
    response_model=BeatGenerateResponse,
)
async def generate_beats(
    project_id: str,
    payload: BeatGenerateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> BeatGenerateResponse:
    """Generate beat outlines for the current chapter context."""
    beats = await editor_service.planning.generate_beats(
        db_session, project_id, current_user.id, payload,
    )
    return BeatGenerateResponse(beats=beats)


@router.post("/{project_id}/editor/expand-beat")
async def expand_beat(
    project_id: str,
    payload: BeatExpandRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> StreamingResponse:
    """Stream prose that expands a selected beat into chapter text."""
    gen = await editor_service.writing.stream_beat_expansion(
        db_session, project_id, current_user.id, payload,
    )
    return sse_response(gen, error_log_message="节拍展开异常")


@router.post("/{project_id}/editor/generate-volumes")
async def generate_volumes(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
    payload: VolumeGenerateRequest | None = None,
) -> StreamingResponse:
    """Stream top-level volume planning output for the project."""
    gen = await editor_service.planning.stream_volume_generation(
        db_session, project_id, current_user.id, payload,
    )
    return sse_response(gen, error_log_message="分卷结构生成异常")


@router.post("/{project_id}/editor/generate-volume-chapters")
async def generate_volume_chapters(
    project_id: str,
    payload: VolumeChaptersRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    editor_service: EditorServiceDep,
) -> StreamingResponse:
    gen = await editor_service.planning.stream_volume_chapters_generation(
        db_session, project_id, current_user.id, payload,
    )
    return sse_response(gen, error_log_message="卷章节生成异常")
