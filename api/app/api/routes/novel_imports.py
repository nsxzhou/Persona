from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile, status
from pydantic import ValidationError

from app.api.deps import CurrentUserDep, DbSessionDep, NovelImportServiceDep
from app.core.domain_errors import UnprocessableEntityError
from app.schemas.novel_imports import (
    NovelImportCommitResponse,
    NovelImportDraftPreview,
    NovelImportDraftUpdateRequest,
    NovelImportProjectMetadata,
)

router = APIRouter(
    prefix="/novel-imports",
    tags=["novel-imports"],
)


@router.post("/preview", response_model=NovelImportDraftPreview, status_code=201)
async def preview_novel_import(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    import_service: NovelImportServiceDep,
    project_name: str = Form(...),
    default_provider_id: str = Form(...),
    default_model: str | None = Form(default=None),
    style_profile_id: str | None = Form(default=None),
    plot_profile_id: str | None = Form(default=None),
    generation_profile: str | None = Form(default=None),
    rights_confirmed: bool = Form(default=False),
    file: UploadFile = File(...),
) -> NovelImportDraftPreview:
    project = _build_project_metadata(
        project_name=project_name,
        default_provider_id=default_provider_id,
        default_model=default_model,
        style_profile_id=style_profile_id,
        plot_profile_id=plot_profile_id,
        generation_profile=generation_profile,
    )
    return await import_service.preview_upload(
        db_session,
        user_id=current_user.id,
        project=project,
        rights_confirmed=rights_confirmed,
        upload_file=file,
    )


@router.patch("/{draft_id}", response_model=NovelImportDraftPreview)
async def update_novel_import_draft(
    draft_id: str,
    payload: NovelImportDraftUpdateRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    import_service: NovelImportServiceDep,
) -> NovelImportDraftPreview:
    return await import_service.update_draft(
        db_session,
        draft_id,
        payload,
        user_id=current_user.id,
    )


@router.post("/{draft_id}/commit", response_model=NovelImportCommitResponse)
async def commit_novel_import(
    draft_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    import_service: NovelImportServiceDep,
) -> NovelImportCommitResponse:
    return await import_service.commit_draft(
        db_session,
        draft_id,
        user_id=current_user.id,
    )


def _build_project_metadata(
    *,
    project_name: str,
    default_provider_id: str,
    default_model: str | None,
    style_profile_id: str | None,
    plot_profile_id: str | None,
    generation_profile: str | None,
) -> NovelImportProjectMetadata:
    parsed_generation_profile: dict[str, Any] | None = None
    if generation_profile and generation_profile.strip():
        try:
            raw_profile = json.loads(generation_profile)
        except json.JSONDecodeError as exc:
            raise UnprocessableEntityError("generation_profile 必须是合法 JSON") from exc
        if not isinstance(raw_profile, dict):
            raise UnprocessableEntityError("generation_profile 必须是 JSON 对象")
        parsed_generation_profile = raw_profile
    try:
        return NovelImportProjectMetadata(
            project_name=project_name,
            default_provider_id=default_provider_id,
            default_model=default_model or None,
            style_profile_id=style_profile_id or None,
            plot_profile_id=plot_profile_id or None,
            generation_profile=parsed_generation_profile,
        )
    except ValidationError as exc:
        raise UnprocessableEntityError("导入项目元数据不完整或格式错误") from exc
