from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import decrypt_secret
from app.db.models import ProviderConfig, StyleAnalysisJob, StyleSampleFile
from app.schemas.style_analysis_jobs import StyleDraft
from app.services.provider_configs import ProviderConfigService

logger = logging.getLogger(__name__)


class StyleAnalysisJobService:
    def __init__(self) -> None:
        self.provider_service = ProviderConfigService()

    async def list(self, session: AsyncSession) -> list[StyleAnalysisJob]:
        result = await session.scalars(
            select(StyleAnalysisJob)
            .options(
                selectinload(StyleAnalysisJob.provider),
                selectinload(StyleAnalysisJob.sample_file),
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
            draft_payload=None,
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
        async with session_factory() as session:
            job = await session.scalar(
                select(StyleAnalysisJob)
                .options(
                    selectinload(StyleAnalysisJob.provider),
                    selectinload(StyleAnalysisJob.sample_file),
                )
                .where(StyleAnalysisJob.status == "pending")
                .order_by(StyleAnalysisJob.created_at.asc())
            )
            if job is None:
                return False

            job.status = "running"
            job.stage = "cleaning"
            job.error_message = None
            job.started_at = datetime.now(UTC)
            await session.commit()

            try:
                text = self._read_sample_text(job.sample_file)
                cleaned_text = self._clean_text(text)
                if not cleaned_text.strip():
                    raise RuntimeError("清洗后没有可分析的有效文本")
                job.sample_file.character_count = len(cleaned_text)
                job.stage = "chunking"
                await session.commit()

                chunks = self._chunk_text(cleaned_text)
                if not chunks:
                    raise RuntimeError("切片后没有可分析的有效文本")
                job.stage = "sampling"
                await session.commit()

                sampled_text = self._build_sample_text(chunks)
                job.stage = "analyzing"
                await session.commit()

                draft_payload = await self._generate_draft(job=job, text=sampled_text)
                job.stage = "assembling"
                await session.commit()

                normalized = StyleDraft.model_validate(draft_payload)
                job.draft_payload = normalized.model_dump(mode="json")
                job.status = "succeeded"
                job.stage = None
                job.completed_at = datetime.now(UTC)
                await session.commit()
            except Exception as exc:
                logger.exception("style analysis job failed", extra={"job_id": job.id})
                job.status = "failed"
                job.stage = None
                job.error_message = str(exc)
                job.completed_at = datetime.now(UTC)
                await session.commit()

        return True

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
        async with session_factory() as session:
            result = await session.scalars(
                select(StyleAnalysisJob).where(
                    StyleAnalysisJob.status == "running",
                    StyleAnalysisJob.started_at.is_not(None),
                    StyleAnalysisJob.started_at < cutoff,
                )
            )
            stale_jobs = list(result.all())
            for job in stale_jobs:
                job.status = "failed"
                job.stage = None
                job.error_message = "分析任务因服务重启中断，请重新提交"
                job.completed_at = datetime.now(UTC)
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

    def _build_sample_text(self, chunks: list[str]) -> str:
        if len(chunks) <= 3:
            return "\n\n".join(chunks)

        middle_index = len(chunks) // 2
        selected = [chunks[0], chunks[middle_index], chunks[-1]]
        return "\n\n".join(selected)

    async def _generate_draft(self, *, job: StyleAnalysisJob, text: str) -> dict:
        provider = job.provider
        settings = get_settings()
        model = init_chat_model(
            model=job.model_name,
            model_provider="openai",
            base_url=provider.base_url,
            api_key=decrypt_secret(provider.api_key_encrypted),
            temperature=0.0,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        prompt = self._build_analysis_prompt(job.style_name, text)
        response = await model.ainvoke([HumanMessage(content=prompt)])
        return self._parse_json_payload(response.content if isinstance(response.content, str) else str(response.content))

    def _build_analysis_prompt(self, style_name: str, text: str) -> str:
        return (
            "你是中文长篇小说文风分析助手。"
            "请基于提供的样本文本，输出严格 JSON，不要附带任何解释。"
            "JSON 必须包含字段："
            "style_name, analysis_summary, global_system_prompt, dimensions, scene_prompts, few_shot_examples。"
            "其中 dimensions 必须含 vocabulary_habits, syntax_rhythm, narrative_perspective, dialogue_traits；"
            "scene_prompts 必须含 dialogue, action, environment；"
            "few_shot_examples 至少返回 2 条，每条含 type 与 text。"
            f"目标风格名称：{style_name}\n\n样本文本：\n{text}"
        )

    def _parse_json_payload(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match is None:
                raise RuntimeError("LLM 返回内容无法解析") from None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise RuntimeError("LLM 返回内容无法解析") from exc
