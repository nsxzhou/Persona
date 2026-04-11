from __future__ import annotations

from typing import Any

from app.db.models import StyleAnalysisJob, StyleProfile
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    AnalysisReport,
    PromptPack,
    StyleSummary,
)


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


def build_profile_result_bundle(profile: StyleProfile) -> tuple[AnalysisReport, StyleSummary, PromptPack]:
    return (
        AnalysisReport.model_validate(profile.analysis_report_payload),
        StyleSummary.model_validate(profile.style_summary_payload),
        PromptPack.model_validate(profile.prompt_pack_payload),
    )


def build_style_profile_response_payload(profile: StyleProfile) -> dict[str, Any]:
    analysis_report, style_summary, prompt_pack = build_profile_result_bundle(profile)
    return {
        "id": profile.id,
        "source_job_id": profile.source_job_id,
        "provider_id": profile.provider_id,
        "model_name": profile.model_name,
        "source_filename": profile.source_filename,
        "style_name": profile.style_name,
        "analysis_report": analysis_report,
        "style_summary": style_summary,
        "prompt_pack": prompt_pack,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
