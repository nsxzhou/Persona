from __future__ import annotations

from typing import Any

from app.db.models import StyleAnalysisJob, StyleProfile
from app.schemas.style_analysis_jobs import AnalysisMeta


def build_job_result_bundle(job: StyleAnalysisJob) -> tuple[
    AnalysisMeta | None,
    str | None,
    str | None,
    str | None,
]:
    if (
        job.analysis_meta_payload
        and job.analysis_report_payload
        and job.style_summary_payload
        and job.prompt_pack_payload
    ):
        return (
            AnalysisMeta.model_validate(job.analysis_meta_payload),
            job.analysis_report_payload,
            job.style_summary_payload,
            job.prompt_pack_payload,
        )

    return None, None, None, None


def build_profile_result_bundle(profile: StyleProfile) -> tuple[str, str, str]:
    return (
        profile.analysis_report_payload,
        profile.style_summary_payload,
        profile.prompt_pack_payload,
    )


def build_style_profile_response_payload(profile: StyleProfile) -> dict[str, Any]:
    analysis_report_markdown, style_summary_markdown, prompt_pack_markdown = (
        build_profile_result_bundle(profile)
    )
    return {
        "id": profile.id,
        "source_job_id": profile.source_job_id,
        "provider_id": profile.provider_id,
        "model_name": profile.model_name,
        "source_filename": profile.source_filename,
        "style_name": profile.style_name,
        "analysis_report_markdown": analysis_report_markdown,
        "style_summary_markdown": style_summary_markdown,
        "prompt_pack_markdown": prompt_pack_markdown,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
