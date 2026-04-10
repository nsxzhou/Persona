from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

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
from app.services.style_analysis_pipeline import (
    StyleAnalysisPipeline,
    StyleAnalysisPipelineResult,
)

logger = logging.getLogger(__name__)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class StyleAnalysisRunContext:
    provider: ProviderConfig
    style_name: str
    model_name: str
    source_filename: str
    cleaned_text: str
    chunks: list[str]
    classification: dict[str, object]


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
        self.checkpointer_factory = StyleAnalysisCheckpointerFactory()

    async def aclose(self) -> None:
        await self.checkpointer_factory.aclose()

    async def list(self, session: AsyncSession) -> list[StyleAnalysisJob]:
        result = await session.scalars(
            select(StyleAnalysisJob)
            .options(
                selectinload(StyleAnalysisJob.provider),
                selectinload(StyleAnalysisJob.sample_file),
                selectinload(StyleAnalysisJob.style_profile),
            )
            .order_by(StyleAnalysisJob.created_at.desc())
        )
        return list(result.all())

    async def get_or_404(self, session: AsyncSession, job_id: str) -> StyleAnalysisJob:
        job = await session.scalar(
            select(StyleAnalysisJob)
            .options(
                selectinload(StyleAnalysisJob.provider),
                selectinload(StyleAnalysisJob.sample_file),
                selectinload(StyleAnalysisJob.style_profile),
            )
            .where(StyleAnalysisJob.id == job_id)
        )
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析任务不存在")
        return job

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
        if not file_name.lower().endswith(".txt"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="仅支持上传 .txt 样本文件",
            )

        raw_bytes = await upload_file.read()
        if not raw_bytes.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="上传的 TXT 文件为空",
            )

        checksum = hashlib.sha256(raw_bytes).hexdigest()
        sample_file = StyleSampleFile(
            original_filename=file_name,
            content_type=upload_file.content_type,
            storage_path="",
            byte_size=len(raw_bytes),
            character_count=None,
            checksum_sha256=checksum,
        )
        session.add(sample_file)
        await session.flush()

        storage_path = self._build_storage_path(sample_file.id)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(raw_bytes)
        sample_file.storage_path = str(storage_path)

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

    def _build_storage_path(self, sample_file_id: str) -> Path:
        settings = get_settings()
        return Path(settings.storage_dir).expanduser() / "style-samples" / f"{sample_file_id}.txt"

    async def process_next_pending(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> bool:
        worker_id = f"style-worker-{uuid.uuid4()}"
        job_id = await self._claim_next_pending_job(session_factory, worker_id=worker_id)
        if job_id is None:
            return False

        await self._run_claimed_job(session_factory, job_id)
        return True

    async def _claim_next_pending_job(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        worker_id: str,
    ) -> str | None:
        settings = get_settings()
        async with session_factory() as session:
            candidate_id = await session.scalar(
                select(StyleAnalysisJob.id)
                .where(
                    StyleAnalysisJob.status == "pending",
                    StyleAnalysisJob.attempt_count < settings.style_analysis_max_attempts,
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
                await session.rollback()
                return None

            await session.commit()
            return candidate_id

    async def _run_claimed_job(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
    ) -> None:
        try:
            context = await self._load_run_context(session_factory, job_id)
            pipeline = await self._build_pipeline(
                provider=context.provider,
                model_name=context.model_name,
                style_name=context.style_name,
                source_filename=context.source_filename,
                stage_callback=lambda stage: self._touch_job_stage(
                    session_factory,
                    job_id,
                    stage=stage,
                ),
            )
            result = await pipeline.run(
                thread_id=job_id,
                cleaned_text=context.cleaned_text,
                chunks=context.chunks,
                classification=context.classification,
                max_concurrency=get_settings().style_analysis_chunk_max_concurrency,
            )
            await self._mark_job_succeeded(session_factory, job_id, result=result)
        except Exception as exc:
            logger.exception("style analysis job failed", extra={"job_id": job_id})
            await self._mark_job_failed(session_factory, job_id, error_message=str(exc))

    async def _load_run_context(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
    ) -> StyleAnalysisRunContext:
        async with session_factory() as session:
            job = await self.get_or_404(session, job_id)
            text = self._read_sample_text(job.sample_file)
            cleaned_text = self._clean_text(text)
            if not cleaned_text.strip():
                raise RuntimeError("清洗后没有可分析的有效文本")

            classification = await self._classify_input(text=cleaned_text)
            chunks = self._chunk_text(cleaned_text)
            if not chunks:
                raise RuntimeError("切片后没有可分析的有效文本")

            classification["uses_batch_processing"] = len(chunks) > 1
            job.sample_file.character_count = len(cleaned_text)
            await session.commit()
            return StyleAnalysisRunContext(
                provider=job.provider,
                style_name=job.style_name,
                model_name=job.model_name,
                source_filename=job.sample_file.original_filename,
                cleaned_text=cleaned_text,
                chunks=chunks,
                classification=classification,
            )

    async def _build_pipeline(
        self,
        *,
        provider: ProviderConfig,
        model_name: str,
        style_name: str,
        source_filename: str,
        stage_callback,
    ) -> StyleAnalysisPipeline:
        return StyleAnalysisPipeline(
            provider=provider,
            model_name=model_name,
            style_name=style_name,
            source_filename=source_filename,
            checkpointer=await self.checkpointer_factory.get(),
            stage_callback=stage_callback,
        )

    async def _touch_job_stage(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        stage: str | None,
    ) -> None:
        async with session_factory() as session:
            job = await self.get_or_404(session, job_id)
            if job.status != "running":
                return
            job.stage = stage
            job.last_heartbeat_at = datetime.now(UTC)
            await session.commit()

    async def _mark_job_succeeded(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        result: StyleAnalysisPipelineResult,
    ) -> None:
        async with session_factory() as session:
            job = await self.get_or_404(session, job_id)
            job.analysis_meta_payload = result.analysis_meta.model_dump(mode="json")
            job.analysis_report_payload = result.analysis_report.model_dump(mode="json")
            job.style_summary_payload = result.style_summary.model_dump(mode="json")
            job.prompt_pack_payload = result.prompt_pack.model_dump(mode="json")
            job.status = "succeeded"
            job.stage = None
            job.error_message = None
            job.completed_at = datetime.now(UTC)
            job.locked_by = None
            job.locked_at = None
            job.last_heartbeat_at = None
            await session.commit()

    async def _mark_job_failed(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        job_id: str,
        *,
        error_message: str,
    ) -> None:
        async with session_factory() as session:
            job = await self.get_or_404(session, job_id)
            job.status = "failed"
            job.stage = None
            job.error_message = error_message
            job.completed_at = datetime.now(UTC)
            job.locked_by = None
            job.locked_at = None
            job.last_heartbeat_at = None
            await session.commit()

    async def run_worker(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        poll_interval_seconds: float,
    ) -> None:
        while True:
            processed = await self.process_next_pending(session_factory)
            if not processed:
                await asyncio.sleep(poll_interval_seconds)

    async def fail_stale_running_jobs(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        stale_after_seconds: int,
    ) -> None:
        cutoff = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
        max_attempts = get_settings().style_analysis_max_attempts
        async with session_factory() as session:
            result = await session.scalars(
                select(StyleAnalysisJob).where(StyleAnalysisJob.status == "running")
            )
            stale_jobs = [
                job
                for job in result.all()
                if (
                    (ensure_utc(job.last_heartbeat_at) or ensure_utc(job.started_at))
                    and (ensure_utc(job.last_heartbeat_at) or ensure_utc(job.started_at)) < cutoff
                )
            ]
            for job in stale_jobs:
                if job.attempt_count >= max_attempts:
                    job.status = "failed"
                    job.error_message = "分析任务重试次数已用尽，请重新提交"
                    job.completed_at = datetime.now(UTC)
                else:
                    job.status = "pending"
                    job.error_message = None
                    job.completed_at = None
                job.stage = None
                job.locked_by = None
                job.locked_at = None
                job.last_heartbeat_at = None
            if stale_jobs:
                await session.commit()

    def _read_sample_text(self, sample_file: StyleSampleFile) -> str:
        raw_bytes = Path(sample_file.storage_path).read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return raw_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise RuntimeError("TXT 文件编码无法识别，请改为 UTF-8 后重试")

    def _clean_text(self, text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        return normalized.strip()

    def _chunk_text(self, text: str, *, chunk_size: int = 4000) -> list[str]:
        paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
        if not paragraphs:
            return []

        chunks: list[str] = []
        current: list[str] = []
        current_length = 0
        for paragraph in paragraphs:
            paragraph_length = len(paragraph)
            if current and current_length + paragraph_length + 2 > chunk_size:
                chunks.append("\n\n".join(current))
                current = [paragraph]
                current_length = paragraph_length
            else:
                current.append(paragraph)
                current_length += paragraph_length + (2 if current_length else 0)
        if current:
            chunks.append("\n\n".join(current))
        return chunks

    async def _classify_input(self, *, text: str) -> dict[str, object]:
        has_timestamps = bool(
            re.search(r"^\s*(\d{1,2}:\d{2}(?::\d{2})?|\[\d{1,2}:\d{2}(?::\d{2})?\])", text, re.MULTILINE)
        )
        has_speaker_labels = bool(re.search(r"^[^\n：:]{1,20}[：:]", text, re.MULTILINE))
        has_noise_markers = bool(re.search(r"(\[.*?\]|（.*?笑.*?）|【.*?】)", text))

        if has_timestamps and has_speaker_labels:
            text_type = "混合文本"
        elif has_timestamps:
            text_type = "口语字幕"
        else:
            text_type = "章节正文"

        if has_timestamps:
            location_indexing = "时间戳"
        elif "\n\n" in text:
            location_indexing = "章节或段落位置"
        else:
            location_indexing = "无法定位"

        return {
            "text_type": text_type,
            "has_timestamps": has_timestamps,
            "has_speaker_labels": has_speaker_labels,
            "has_noise_markers": has_noise_markers,
            "uses_batch_processing": False,
            "location_indexing": location_indexing,
            "noise_notes": "检测到显著噪声标记。" if has_noise_markers else "未发现显著噪声。",
        }
