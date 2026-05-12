from __future__ import annotations

from dataclasses import dataclass

from app.services.llm_provider import LLMProviderService
from app.services.novel_chapter_rewrite_jobs import NovelChapterRewriteJobService
from app.services.novel_workflow_checkpointer import NovelWorkflowCheckpointerFactory
from app.services.novel_workflow_lifecycle import NovelWorkflowLifecycleService
from app.services.novel_workflow_storage import NovelWorkflowStorageService
from app.services.novel_workflows import NovelWorkflowService
from app.services.plot_profiles import PlotProfileService
from app.services.project_chapters import ProjectChapterService
from app.services.projects import ProjectService
from app.services.prompt_stack import PromptStackService
from app.services.provider_configs import ProviderConfigService
from app.services.style_profiles import StyleProfileService


@dataclass(frozen=True)
class ProjectServiceGraph:
    provider_service: ProviderConfigService
    project_service: ProjectService
    project_chapter_service: ProjectChapterService
    prompt_stack_service: PromptStackService
    style_profile_service: StyleProfileService
    plot_profile_service: PlotProfileService


@dataclass(frozen=True)
class NovelWorkflowServiceGraph:
    provider_service: ProviderConfigService
    project_service: ProjectService
    project_chapter_service: ProjectChapterService
    prompt_stack_service: PromptStackService
    style_profile_service: StyleProfileService
    plot_profile_service: PlotProfileService
    workflow_service: NovelWorkflowService
    workflow_lifecycle_service: NovelWorkflowLifecycleService
    storage_service: NovelWorkflowStorageService
    checkpointer_factory: NovelWorkflowCheckpointerFactory
    llm_service: LLMProviderService


def build_project_service_graph(
    *,
    provider_service: ProviderConfigService | None = None,
    project_service: ProjectService | None = None,
    project_chapter_service: ProjectChapterService | None = None,
) -> ProjectServiceGraph:
    provider_service = provider_service or ProviderConfigService()
    project_service = project_service or ProjectService(provider_service=provider_service)
    project_chapter_service = project_chapter_service or ProjectChapterService(
        project_service=project_service
    )
    prompt_stack_service = PromptStackService(
        project_service=project_service,
        chapter_service=project_chapter_service,
    )
    return ProjectServiceGraph(
        provider_service=provider_service,
        project_service=project_service,
        project_chapter_service=project_chapter_service,
        prompt_stack_service=prompt_stack_service,
        style_profile_service=StyleProfileService(),
        plot_profile_service=PlotProfileService(),
    )


def build_novel_workflow_service_graph(
    *,
    provider_service: ProviderConfigService | None = None,
    project_service: ProjectService | None = None,
    project_chapter_service: ProjectChapterService | None = None,
    prompt_stack_service: PromptStackService | None = None,
    style_profile_service: StyleProfileService | None = None,
    plot_profile_service: PlotProfileService | None = None,
    storage_service: NovelWorkflowStorageService | None = None,
    lifecycle_service: NovelWorkflowLifecycleService | None = None,
    checkpointer_factory: NovelWorkflowCheckpointerFactory | None = None,
    llm_service: LLMProviderService | None = None,
) -> NovelWorkflowServiceGraph:
    if project_service is None or project_chapter_service is None or prompt_stack_service is None:
        project_graph = build_project_service_graph(
            provider_service=provider_service,
            project_service=project_service,
            project_chapter_service=project_chapter_service,
        )
        provider_service = project_graph.provider_service
        project_service = project_service or project_graph.project_service
        project_chapter_service = project_chapter_service or project_graph.project_chapter_service
        prompt_stack_service = prompt_stack_service or project_graph.prompt_stack_service
        style_profile_service = style_profile_service or project_graph.style_profile_service
        plot_profile_service = plot_profile_service or project_graph.plot_profile_service
    else:
        provider_service = provider_service or ProviderConfigService()
        style_profile_service = style_profile_service or StyleProfileService()
        plot_profile_service = plot_profile_service or PlotProfileService()

    storage_service = storage_service or NovelWorkflowStorageService()
    workflow_service = NovelWorkflowService(
        storage_service=storage_service,
        project_service=project_service,
        project_chapter_service=project_chapter_service,
        provider_service=provider_service,
    )
    lifecycle_service = lifecycle_service or NovelWorkflowLifecycleService(
        repository=workflow_service.repository
    )
    return NovelWorkflowServiceGraph(
        provider_service=provider_service,
        project_service=project_service,
        project_chapter_service=project_chapter_service,
        prompt_stack_service=prompt_stack_service,
        style_profile_service=style_profile_service,
        plot_profile_service=plot_profile_service,
        workflow_service=workflow_service,
        workflow_lifecycle_service=lifecycle_service,
        storage_service=storage_service,
        checkpointer_factory=checkpointer_factory or NovelWorkflowCheckpointerFactory(),
        llm_service=llm_service or LLMProviderService(),
    )


def build_novel_chapter_rewrite_job_service(
    *,
    workflow_service: NovelWorkflowService,
    chapter_service: ProjectChapterService,
) -> NovelChapterRewriteJobService:
    return NovelChapterRewriteJobService(
        workflow_service=workflow_service,
        chapter_service=chapter_service,
    )
