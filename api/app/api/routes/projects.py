from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUserDep, DbSessionDep, ProjectServiceDep, StyleProfileServiceDep
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate, EditorCompletionRequest
from app.services.llm_provider import LLMProviderService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
    include_archived: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
) -> list[ProjectResponse]:
    projects = await project_service.list(
        db_session,
        user_id=current_user.id,
        include_archived=include_archived,
        offset=offset,
        limit=limit,
    )
    return [ProjectResponse.model_validate(project) for project in projects]

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.create(
        db_session,
        payload,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.get_or_404(
        db_session,
        project_id,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.update(
        db_session,
        project_id,
        payload,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)

@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.archive(
        db_session,
        project_id,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)

@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: str,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    project = await project_service.restore(
        db_session,
        project_id,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)

@router.post("/{project_id}/editor/complete")
async def editor_complete(
    project_id: str,
    payload: EditorCompletionRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
    project_service: ProjectServiceDep,
    style_profile_service: StyleProfileServiceDep,
) -> StreamingResponse:
    project = await project_service.get_or_404(
        db_session,
        project_id,
        user_id=current_user.id,
    )
    if not project.style_profile_id:
        raise HTTPException(status_code=400, detail="项目未挂载风格档案")
        
    style_profile = await style_profile_service.get_or_404(
        db_session,
        project.style_profile_id,
        user_id=current_user.id,
    )
    system_prompt = style_profile.prompt_pack_payload
    llm_service = LLMProviderService()
    
    async def sse_generator():
        try:
            async for chunk in llm_service.stream_completion(
                provider_config=project.provider,
                system_prompt=system_prompt,
                user_context=payload.text_before_cursor
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            logger.exception("AI 续写异常")
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")
