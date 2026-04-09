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
from app.db.models import StyleAnalysisJob, StyleSampleFile
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    AnalysisReport,
    PromptPack,
    StyleAnalysisJobResponse,
    StyleSummary,
)
from app.services.provider_configs import ProviderConfigService

logger = logging.getLogger(__name__)

SHARED_ANALYSIS_RULES = """
你必须遵守以下规则：
1. 所有结论必须证据优先，不得编造不存在的设定、说话人或风格特征。
2. 输出必须使用中文简体，返回严格 JSON，不附带解释。
3. 如果证据不足，必须明确使用低置信或弱判断，不得伪装成确定结论。
4. 关注文本类型、索引方式、噪声、批处理条件，并在后续分析中保持一致。
5. 3.1 到 3.12 的专题不能缺失，但某一节证据稀少时允许给出“当前样本中证据有限”的说明。
""".strip()


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
                    selectinload(StyleAnalysisJob.style_profile),
                )
                .where(StyleAnalysisJob.status == "pending")
                .order_by(StyleAnalysisJob.created_at.asc())
            )
            if job is None:
                return False

            job.status = "running"
            job.stage = "classifying_input"
            job.error_message = None
            job.started_at = datetime.now(UTC)
            await session.commit()

            try:
                text = self._read_sample_text(job.sample_file)
                cleaned_text = self._clean_text(text)
                if not cleaned_text.strip():
                    raise RuntimeError("清洗后没有可分析的有效文本")
                job.sample_file.character_count = len(cleaned_text)
                self._current_provider = job.provider
                self._current_model_name = job.model_name
                classification = await self._classify_input(text=cleaned_text)

                chunks = self._chunk_text(cleaned_text)
                if not chunks:
                    raise RuntimeError("切片后没有可分析的有效文本")

                classification["uses_batch_processing"] = len(chunks) > 1

                job.stage = "analyzing_chunks"
                await session.commit()

                chunk_analyses = await self._analyze_chunks(
                    chunks=chunks,
                    classification=classification,
                )

                job.stage = "aggregating"
                await session.commit()
                merged_analysis = await self._merge_chunk_analyses(
                    chunk_analyses=chunk_analyses,
                    classification=classification,
                )

                job.stage = "reporting"
                await session.commit()
                report = AnalysisReport.model_validate(
                    await self._build_analysis_report(
                        merged_analysis=merged_analysis,
                        classification=classification,
                    )
                )

                job.stage = "summarizing"
                await session.commit()
                style_summary = StyleSummary.model_validate(
                    await self._build_style_summary(report=report.model_dump(mode="json"))
                )

                job.stage = "composing_prompt_pack"
                await session.commit()
                prompt_pack = PromptPack.model_validate(
                    await self._build_prompt_pack(
                        report=report.model_dump(mode="json"),
                        style_summary=style_summary.model_dump(mode="json"),
                    )
                )

                analysis_meta = AnalysisMeta(
                    source_filename=job.sample_file.original_filename,
                    model_name=job.model_name,
                    text_type=classification["text_type"],
                    has_timestamps=classification["has_timestamps"],
                    has_speaker_labels=classification["has_speaker_labels"],
                    has_noise_markers=classification["has_noise_markers"],
                    uses_batch_processing=classification["uses_batch_processing"],
                    location_indexing=classification["location_indexing"],
                    chunk_count=len(chunks),
                )

                job.analysis_meta_payload = analysis_meta.model_dump(mode="json")
                job.analysis_report_payload = report.model_dump(mode="json")
                job.style_summary_payload = style_summary.model_dump(mode="json")
                job.prompt_pack_payload = prompt_pack.model_dump(mode="json")
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
            finally:
                self._current_provider = None
                self._current_model_name = None

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

    async def _classify_input(self, *, text: str) -> dict:
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

    async def _analyze_chunks(self, *, chunks: list[str], classification: dict) -> list[dict]:
        analyses: list[dict] = []
        for index, chunk in enumerate(chunks):
            prompt = self._build_chunk_analysis_prompt(
                chunk=chunk,
                chunk_index=index,
                classification=classification,
                chunk_count=len(chunks),
            )
            analyses.append(await self._invoke_json_prompt(prompt))
        return analyses

    async def _merge_chunk_analyses(self, *, chunk_analyses: list[dict], classification: dict) -> dict:
        if len(chunk_analyses) == 1:
            return {
                "classification": classification,
                "sections": chunk_analyses[0].get("sections", []),
            }

        prompt = self._build_merge_prompt(chunk_analyses=chunk_analyses, classification=classification)
        return await self._invoke_json_prompt(prompt)

    async def _build_analysis_report(self, *, merged_analysis: dict, classification: dict) -> dict:
        prompt = self._build_report_prompt(
            merged_analysis=merged_analysis,
            classification=classification,
        )
        return await self._invoke_json_prompt(prompt)

    async def _build_style_summary(self, *, report: dict) -> dict:
        prompt = self._build_style_summary_prompt(report=report)
        return await self._invoke_json_prompt(prompt)

    async def _build_prompt_pack(self, *, report: dict, style_summary: dict) -> dict:
        prompt = self._build_prompt_pack_prompt(report=report, style_summary=style_summary)
        return await self._invoke_json_prompt(prompt)

    async def _invoke_json_prompt(self, prompt: str) -> dict:
        provider = getattr(self, "_current_provider", None)
        model_name = getattr(self, "_current_model_name", None)
        if provider is None or model_name is None:
            raise RuntimeError("分析上下文缺失：尚未绑定 Provider 或模型")

        settings = get_settings()
        model = init_chat_model(
            model=model_name,
            model_provider="openai",
            base_url=provider.base_url,
            api_key=decrypt_secret(provider.api_key_encrypted),
            temperature=0.0,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        response = await model.ainvoke([HumanMessage(content=prompt)])
        content = response.content if isinstance(response.content, str) else str(response.content)
        return self._parse_json_payload(content)

    def _build_chunk_analysis_prompt(
        self,
        *,
        chunk: str,
        chunk_index: int,
        classification: dict,
        chunk_count: int,
    ) -> str:
        sections = "\n".join(f"- {section} {title}" for section, title in SECTION_TITLES)
        return (
            f"{SHARED_ANALYSIS_RULES}\n\n"
            "你正在执行分块分析阶段。请基于当前 chunk 的文本，只输出严格 JSON。\n"
            "JSON 结构：{sections:[{section,title,overview,findings:[{label,summary,frequency,confidence,is_weak_judgment,evidence:[{excerpt,location}]}]}]}\n"
            "要求：\n"
            "1. sections 必须覆盖 3.1 到 3.12。\n"
            "2. 每节可以只有 1-3 条 finding；证据不足时仍保留该节并降低置信度。\n"
            "3. excerpt 必须来自样本文本，不得编造。\n"
            "4. confidence 只能是 high/medium/low。\n\n"
            f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
            f"当前 chunk：{chunk_index + 1}/{chunk_count}\n"
            f"章节结构：\n{sections}\n\n"
            f"样本文本：\n{chunk}"
        )

    def _build_merge_prompt(self, *, chunk_analyses: list[dict], classification: dict) -> str:
        sections = "\n".join(f"- {section} {title}" for section, title in SECTION_TITLES)
        return (
            f"{SHARED_ANALYSIS_RULES}\n\n"
            "你正在执行全局聚合阶段。请把多个 chunk 的分析结果合并成统一 JSON。\n"
            "要求：同义归并、重复证据去重、弱判断保留、多说话人差异不抹平。\n"
            "JSON 结构：{sections:[{section,title,overview,findings:[{label,summary,frequency,confidence,is_weak_judgment,evidence:[{excerpt,location}]}]}]}\n\n"
            f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
            f"章节结构：\n{sections}\n\n"
            f"待合并结果：\n{json.dumps(chunk_analyses, ensure_ascii=False)}"
        )

    def _build_report_prompt(self, *, merged_analysis: dict, classification: dict) -> str:
        return (
            f"{SHARED_ANALYSIS_RULES}\n\n"
            "你正在把聚合结果整理成最终分析报告。请只输出严格 JSON。\n"
            "JSON 结构：\n"
            "{executive_summary:{summary,representative_evidence:[{excerpt,location}]},"
            "basic_assessment:{text_type,multi_speaker,batch_mode,location_indexing,noise_handling},"
            "sections:[{section,title,overview,findings:[{label,summary,frequency,confidence,is_weak_judgment,evidence:[{excerpt,location}]}]}],"
            "appendix}\n"
            "要求：sections 必须覆盖 3.1 到 3.12。\n\n"
            f"输入判定：{json.dumps(classification, ensure_ascii=False)}\n"
            f"聚合结果：\n{json.dumps(merged_analysis, ensure_ascii=False)}"
        )

    def _build_style_summary_prompt(self, *, report: dict) -> str:
        return (
            f"{SHARED_ANALYSIS_RULES}\n\n"
            "你正在从完整分析报告提炼可编辑风格摘要。请只输出严格 JSON。\n"
            "JSON 结构："
            "{style_name,style_positioning,core_features,lexical_preferences,rhythm_profile,punctuation_profile,"
            "imagery_and_themes,scene_strategies:[{scene,instruction}],avoid_or_rare,generation_notes}\n"
            "要求：不要引入报告中不存在的结论；尽量高密度、可用于后续生成。\n\n"
            f"分析报告：\n{json.dumps(report, ensure_ascii=False)}"
        )

    def _build_prompt_pack_prompt(self, *, report: dict, style_summary: dict) -> str:
        return (
            "你是一位小说写作 prompt 编排器。"
            "请基于完整分析报告和当前风格摘要，生成一个全局可复用的风格母 prompt 包。"
            "不要绑定具体项目剧情，不要引入报告中没有的结论。"
            "只输出严格 JSON。\n"
            "JSON 结构："
            "{system_prompt,scene_prompts:{dialogue,action,environment},hard_constraints,"
            "style_controls:{tone,rhythm,evidence_anchor},few_shot_slots:[{label,type,text,purpose}]}\n\n"
            f"分析报告：\n{json.dumps(report, ensure_ascii=False)}\n\n"
            f"当前风格摘要：\n{json.dumps(style_summary, ensure_ascii=False)}"
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
