from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import defer, joinedload

from app.core.config import get_settings
from app.db.models import ProviderConfig, StyleAnalysisJob, StyleSampleFile
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    AnalysisReport,
    PromptPack,
    StyleSummary,
)
from app.services.provider_configs import ProviderConfigService
from app.services.style_analysis_checkpointer import StyleAnalysisCheckpointerFactory
from app.services.style_analysis_storage import StyleAnalysisStorageService

logger = logging.getLogger(__name__)


def build_job_result_bundle(job: StyleAnalysisJob) -> tuple[
    AnalysisMeta | None,
    AnalysisReport | None,
    StyleSummary | None,
    PromptPack | None,
]:
    if (
        job.analysis_meta_payload
        and job.analysis_report_payload
        and job.style_summary_payload
        and job.prompt_pack_payload
    ):
        return (
            AnalysisMeta.model_validate(job.analysis_meta_payload),
            AnalysisReport.model_validate(job.analysis_report_payload),
            StyleSummary.model_validate(job.style_summary_payload),
            PromptPack.model_validate(job.prompt_pack_payload),
        )

    return None, None, None, None


def build_profile_result_bundle(profile) -> tuple[AnalysisReport, StyleSummary, PromptPack]:
    return (
        AnalysisReport.model_validate(profile.analysis_report_payload),
        StyleSummary.model_validate(profile.style_summary_payload),
        PromptPack.model_validate(profile.prompt_pack_payload),
    )


class StyleAnalysisJobService:
    def __init__(self) -> None:
        self.provider_service = ProviderConfigService()

    async def list(
        self,
        session: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[StyleAnalysisJob]:
        limit = min(max(limit, 1), 100)
        result = await session.stream_scalars(
            select(StyleAnalysisJob)
            .options(
                defer(StyleAnalysisJob.analysis_meta_payload),
                defer(StyleAnalysisJob.analysis_report_payload),
                defer(StyleAnalysisJob.style_summary_payload),
                defer(StyleAnalysisJob.prompt_pack_payload),
                joinedload(StyleAnalysisJob.provider),
                joinedload(StyleAnalysisJob.sample_file),
                joinedload(StyleAnalysisJob.style_profile),
            )
            .order_by(StyleAnalysisJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [job async for job in result]

    async def get_or_404(
        self, session: AsyncSession, job_id: str, *, include_payloads: bool = True
    ) -> StyleAnalysisJob:
        stmt = select(StyleAnalysisJob).options(
            joinedload(StyleAnalysisJob.provider),
            joinedload(StyleAnalysisJob.sample_file),
            joinedload(StyleAnalysisJob.style_profile),
        )
        if not include_payloads:
            stmt = stmt.options(
                defer(StyleAnalysisJob.analysis_meta_payload),
                defer(StyleAnalysisJob.analysis_report_payload),
                defer(StyleAnalysisJob.style_summary_payload),
                defer(StyleAnalysisJob.prompt_pack_payload),
            )
        job = await session.scalar(stmt.where(StyleAnalysisJob.id == job_id))
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析任务不存在")
        return job

    async def _get_payload_or_409(
        self,
        session: AsyncSession,
        job_id: str,
        *,
        payload_column,
        parser,
        not_ready_detail: str,
    ):
        row = await session.execute(
            select(StyleAnalysisJob.status, payload_column).where(StyleAnalysisJob.id == job_id)
        )
        result = row.one_or_none()
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析任务不存在")
        job_status, payload = result
        if job_status != "succeeded" or payload is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=not_ready_detail)
        return parser(payload)

    async def get_analysis_meta_or_409(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> AnalysisMeta:
        return await self._get_payload_or_409(
            session,
            job_id,
            payload_column=StyleAnalysisJob.analysis_meta_payload,
            parser=AnalysisMeta.model_validate,
            not_ready_detail="分析任务尚未完成，暂无法读取元数据",
        )

    async def get_analysis_report_or_409(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> AnalysisReport:
        return await self._get_payload_or_409(
            session,
            job_id,
            payload_column=StyleAnalysisJob.analysis_report_payload,
            parser=AnalysisReport.model_validate,
            not_ready_detail="分析任务尚未完成，暂无法读取分析报告",
        )

    async def get_style_summary_or_409(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> StyleSummary:
        return await self._get_payload_or_409(
            session,
            job_id,
            payload_column=StyleAnalysisJob.style_summary_payload,
            parser=StyleSummary.model_validate,
            not_ready_detail="分析任务尚未完成，暂无法读取风格摘要",
        )

    async def get_prompt_pack_or_409(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> PromptPack:
        return await self._get_payload_or_409(
            session,
            job_id,
            payload_column=StyleAnalysisJob.prompt_pack_payload,
            parser=PromptPack.model_validate,
            not_ready_detail="分析任务尚未完成，暂无法读取 Prompt 包",
        )

    async def claim_job_for_worker(
        self,
        session: AsyncSession,
        *,
        worker_id: str,
        max_attempts: int,
    ) -> str | None:
        candidate_id = await session.scalar(
            select(StyleAnalysisJob.id)
            .where(
                StyleAnalysisJob.status == "pending",
                StyleAnalysisJob.attempt_count < max_attempts,
            )
            .order_by(StyleAnalysisJob.created_at.asc())
            .limit(1)
        )
        if candidate_id is None:
            return None

        now = datetime.now(UTC)
        result = await session.execute(
            update(StyleAnalysisJob)
            .where(
                StyleAnalysisJob.id == candidate_id,
                StyleAnalysisJob.status == "pending",
            )
            .values(
                status="running",
                stage="preparing_input",
                error_message=None,
                started_at=now,
                completed_at=None,
                locked_by=worker_id,
                locked_at=now,
                last_heartbeat_at=now,
                attempt_count=StyleAnalysisJob.attempt_count + 1,
            )
        )
        if result.rowcount != 1:
            return None

        return candidate_id

    async def create(
        self,
        session: AsyncSession,
        *,
        style_name: str,
        provider_id: str,
        model: str | None,
        upload_file: UploadFile,
    ) -> StyleAnalysisJob:
        provider = await self.provider_service.ensure_enabled(session, provider_id)
        file_name = (upload_file.filename or "").strip()

        sample_file = StyleSampleFile(
            original_filename=file_name,
            content_type=upload_file.content_type,
            storage_path="",
            byte_size=0,
            character_count=None,
            checksum_sha256="",
        )
        session.add(sample_file)
        await session.flush()

        storage_service = StyleAnalysisStorageService()
        storage_path, total_bytes, checksum = await storage_service.save_file(
            sample_file.id,
            upload_file,
        )

        sample_file.storage_path = storage_path
        sample_file.byte_size = total_bytes
        sample_file.checksum_sha256 = checksum

        selected_model = model.strip() if model else ""
        job = StyleAnalysisJob(
            style_name=style_name.strip(),
            provider_id=provider.id,
            model_name=selected_model or provider.default_model,
            sample_file_id=sample_file.id,
            status="pending",
            stage=None,
            error_message=None,
            analysis_meta_payload=None,
            analysis_report_payload=None,
            style_summary_payload=None,
            prompt_pack_payload=None,
            locked_by=None,
            locked_at=None,
            last_heartbeat_at=None,
            attempt_count=0,
        )
        session.add(job)
        await session.flush()

        return await self.get_or_404(session, job.id)

