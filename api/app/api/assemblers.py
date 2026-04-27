from __future__ import annotations

from typing import Any

from app.db.models import PlotAnalysisJob, PlotProfile, StyleAnalysisJob, StyleProfile
from app.schemas.plot_analysis_jobs import (
    PlotAnalysisJobResponse,
    PlotAnalysisMeta,
    PlotProfileEmbeddedResponse,
)
from app.schemas.style_analysis_jobs import (
    AnalysisMeta,
    StyleAnalysisJobResponse,
    StyleProfileEmbeddedResponse,
)
from app.schemas.prompt_profiles import (
    derive_plot_writing_guide_profile,
    derive_voice_profile,
)


def build_job_result_bundle(job: StyleAnalysisJob) -> tuple[
    AnalysisMeta | None,
    str | None,
    str | None,
]:
    if (
        job.analysis_meta_payload
        and job.analysis_report_payload
        and job.voice_profile_payload
    ):
        return (
            AnalysisMeta.model_validate(job.analysis_meta_payload),
            job.analysis_report_payload,
            job.voice_profile_payload,
        )

    return None, None, None


def build_profile_result_bundle(profile: StyleProfile) -> tuple[str, str]:
    return (
        profile.analysis_report_payload,
        profile.voice_profile_payload,
    )


def build_plot_job_result_bundle(job: PlotAnalysisJob) -> tuple[
    PlotAnalysisMeta | None,
    str | None,
    str | None,
]:
    if (
        job.analysis_meta_payload
        and job.analysis_report_payload
        and job.story_engine_payload
    ):
        return (
            PlotAnalysisMeta.model_validate(job.analysis_meta_payload),
            job.analysis_report_payload,
            job.story_engine_payload,
        )

    return None, None, None


def build_plot_profile_result_bundle(profile: PlotProfile) -> tuple[str, str]:
    return (
        profile.analysis_report_payload,
        profile.story_engine_payload,
    )


def build_style_profile_response_payload(profile: StyleProfile) -> dict[str, Any]:
    analysis_report_markdown, voice_profile_markdown = (
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
        "voice_profile_payload": derive_voice_profile(voice_profile_markdown),
        "voice_profile_markdown": voice_profile_markdown,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def build_plot_profile_response_payload(profile: PlotProfile) -> dict[str, Any]:
    analysis_report_markdown, story_engine_markdown = (
        build_plot_profile_result_bundle(profile)
    )
    return {
        "id": profile.id,
        "source_job_id": profile.source_job_id,
        "provider_id": profile.provider_id,
        "model_name": profile.model_name,
        "source_filename": profile.source_filename,
        "plot_name": profile.plot_name,
        "analysis_report_markdown": analysis_report_markdown,
        "story_engine_payload": derive_plot_writing_guide_profile(story_engine_markdown),
        "story_engine_markdown": story_engine_markdown,
        "plot_skeleton_markdown": profile.plot_skeleton_payload,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def build_style_profile_embedded_response(
    profile: StyleProfile | None,
) -> StyleProfileEmbeddedResponse | None:
    if profile is None:
        return None
    return StyleProfileEmbeddedResponse(**build_style_profile_response_payload(profile))


def build_plot_profile_embedded_response(
    profile: PlotProfile | None,
) -> PlotProfileEmbeddedResponse | None:
    if profile is None:
        return None
    return PlotProfileEmbeddedResponse(**build_plot_profile_response_payload(profile))


def build_job_detail_response(job: StyleAnalysisJob) -> StyleAnalysisJobResponse:
    style_profile = build_style_profile_embedded_response(job.style_profile)
    analysis_meta, analysis_report_markdown, voice_profile_markdown = (
        build_job_result_bundle(job)
    )
    return StyleAnalysisJobResponse(
        id=job.id,
        style_name=job.style_name,
        provider_id=job.provider_id,
        model_name=job.model_name,
        status=job.status,
        stage=job.stage,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        pause_requested_at=getattr(job, "pause_requested_at", None),
        provider=job.provider,
        sample_file=job.sample_file,
        style_profile_id=job.style_profile_id,
        style_profile=style_profile,
        analysis_meta=analysis_meta,
        analysis_report_markdown=analysis_report_markdown,
        voice_profile_payload=(
            derive_voice_profile(voice_profile_markdown)
            if voice_profile_markdown is not None
            else None
        ),
        voice_profile_markdown=voice_profile_markdown,
    )


def build_plot_job_detail_response(job: PlotAnalysisJob) -> PlotAnalysisJobResponse:
    plot_profile = build_plot_profile_embedded_response(job.plot_profile)
    story_engine_markdown = job.story_engine_payload
    return PlotAnalysisJobResponse(
        id=job.id,
        plot_name=job.plot_name,
        provider_id=job.provider_id,
        model_name=job.model_name,
        status=job.status,
        stage=job.stage,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        pause_requested_at=getattr(job, "pause_requested_at", None),
        provider=job.provider,
        sample_file=job.sample_file,
        plot_profile_id=job.plot_profile_id,
        plot_profile=plot_profile,
        analysis_report_markdown=job.analysis_report_payload,
        story_engine_payload=(
            derive_plot_writing_guide_profile(story_engine_markdown)
            if story_engine_markdown is not None
            else None
        ),
        story_engine_markdown=story_engine_markdown,
        plot_skeleton_markdown=job.plot_skeleton_payload,
    )
