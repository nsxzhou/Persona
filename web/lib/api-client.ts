import type {
  AnalysisMeta,
  AnalysisReportMarkdown,
  ConnectionTestResponse,
  ConceptGeneratePayload,
  ConceptGenerateResult,
  GenerationProfile,
  LoginPayload,
  NovelWorkflow,
  NovelWorkflowCreatePayload,
  NovelWorkflowDecisionPayload,
  NovelWorkflowListItem,
  NovelWorkflowLogs,
  NovelBeatWorkflowResult,
  NovelMemoryWorkflowResult,
  NovelWorkflowStatusSnapshot,
  Project,
  SetupResponse,
  SetupStatusResponse,
  ProjectChapter,
  ProjectChapterUpdate,
  ProjectPayload,
  ProjectUpdatePayload,
  ProjectSummary,
  ProjectBible,
  ProjectBibleUpdate,
  PlotAnalysisJob,
  PlotAnalysisJobCreatePayload,
  PlotAnalysisJobListItem,
  PlotAnalysisJobLogs,
  PlotAnalysisJobStatusSnapshot,
  PlotAnalysisMeta,
  PlotAnalysisReportMarkdown,
  PlotProfile,
  PlotProfileCreatePayload,
  PlotProfileListItem,
  PlotProfileUpdatePayload,
  PlotSkeletonMarkdown,
  StoryEngineMarkdown,
  ProviderConfig,
  ProviderPayload,
  SetupPayload,
  StyleAnalysisJob,
  StyleAnalysisJobCreatePayload,
  StyleAnalysisJobListItem,
  StyleAnalysisJobLogs,
  StyleAnalysisJobStatusSnapshot,
  StyleProfile,
  StyleProfileCreatePayload,
  StyleProfileListItem,
  VoiceProfileMarkdown,
  StyleProfileUpdatePayload,
  User,
} from "@/lib/types";

type Requester = {
  <T>(path: string, init?: RequestInit): Promise<T>;
  raw: (path: string, init?: RequestInit) => Promise<Response>;
};

type RegenerateOptions = {
  previousOutput?: string;
  userFeedback?: string;
};

export type { RegenerateOptions };

function regenerateFields(options?: RegenerateOptions): Record<string, string> {
  if (!options) return {};
  const out: Record<string, string> = {};
  if (options.previousOutput !== undefined && options.previousOutput !== null) {
    out.previous_output = options.previousOutput;
  }
  if (options.userFeedback !== undefined && options.userFeedback !== null) {
    out.feedback = options.userFeedback;
  }
  return out;
}

function buildSseResponse(text: string): Response {
  const payload = `data: ${JSON.stringify(text)}\n\n`;
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(payload));
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { "content-type": "text/event-stream" },
  });
}

function parseMarkdownConcepts(markdown: string): ConceptGenerateResult {
  const concepts = markdown
    .split(/^###\s+/m)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const [titleLine, ...rest] = part.split("\n");
      return {
        title: titleLine.trim(),
        synopsis: rest.join("\n").trim(),
      };
    })
    .filter((item) => item.title && item.synopsis);
  return { concepts };
}

function parseMemoryBundle(markdown: string): {
  proposedCharactersStatus: string;
  proposedRuntimeState: string;
  proposedRuntimeThreads: string;
} {
  const sections = new Map<string, string>();
  const regex = /^##\s+([^\n]+)\n([\s\S]*?)(?=^##\s+|\Z)/gm;
  for (const match of markdown.matchAll(regex)) {
    sections.set(match[1].trim(), match[2].trim());
  }
  return {
    proposedCharactersStatus: sections.get("角色动态状态") ?? "",
    proposedRuntimeState: sections.get("运行时状态") ?? "",
    proposedRuntimeThreads: sections.get("伏笔与线索追踪") ?? "",
  };
}

export function createApiClient(request: Requester) {
  const pollNovelWorkflow = async (runId: string): Promise<NovelWorkflowStatusSnapshot> => {
    while (true) {
      const status = await request<NovelWorkflowStatusSnapshot>(`/api/v1/novel-workflows/${runId}/status`);
      if (status.status === "succeeded" || status.status === "paused" || status.status === "failed") {
        return status;
      }
      await new Promise((resolve) => setTimeout(resolve, 10));
    }
  };

  const createNovelWorkflowAndWait = async (
    payload: NovelWorkflowCreatePayload,
  ): Promise<{ run: NovelWorkflowListItem; status: NovelWorkflowStatusSnapshot }> => {
    const run = await request<NovelWorkflowListItem>("/api/v1/novel-workflows", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const status = await pollNovelWorkflow(run.id);
    if (status.status === "failed") {
      throw new Error(status.error_message || "工作流执行失败");
    }
    return { run, status };
  };

  return {
    getSetupStatus: () => request<SetupStatusResponse>("/api/v1/setup/status"),
    setup: (payload: SetupPayload) =>
      request<SetupResponse>("/api/v1/setup", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    login: (payload: LoginPayload) =>
      request<User>("/api/v1/login", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    logout: () =>
      request<void>("/api/v1/logout", {
        method: "POST",
      }),
    deleteAccount: () =>
      request<void>("/api/v1/account", {
        method: "DELETE",
      }),
    getCurrentUser: () => request<User>("/api/v1/me"),
    getProviderConfigs: () => request<ProviderConfig[]>("/api/v1/provider-configs"),
    createProviderConfig: (payload: ProviderPayload) =>
      request<ProviderConfig>("/api/v1/provider-configs", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updateProviderConfig: (id: string, payload: Partial<ProviderPayload>) =>
      request<ProviderConfig>(`/api/v1/provider-configs/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    testProviderConfig: (id: string) =>
      request<ConnectionTestResponse>(`/api/v1/provider-configs/${id}/test`, {
        method: "POST",
      }),
    deleteProviderConfig: (id: string) =>
      request<void>(`/api/v1/provider-configs/${id}`, {
        method: "DELETE",
      }),
    getProjects: (params?: { includeArchived?: boolean; offset?: number; limit?: number }) => {
      const includeArchived = params?.includeArchived ?? false;
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<ProjectSummary[]>(
        `/api/v1/projects?include_archived=${includeArchived}&offset=${offset}&limit=${limit}`
      );
    },
    getProject: (id: string) => request<Project>(`/api/v1/projects/${id}`),
    getProjectBible: (id: string) => request<ProjectBible>(`/api/v1/projects/${id}/bible`),
    updateProjectBible: (id: string, payload: Partial<ProjectBibleUpdate>) =>
      request<ProjectBible>(`/api/v1/projects/${id}/bible`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    exportProject: async (id: string, format: "txt" | "epub") => {
      const response = await request.raw(`/api/v1/projects/${id}/export?format=${format}`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Failed to export project");
      }
      return response.blob();
    },
    createProject: (payload: ProjectPayload) =>
      request<Project>("/api/v1/projects", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updateProject: (id: string, payload: Partial<ProjectUpdatePayload>) =>
      request<Project>(`/api/v1/projects/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    getProjectChapters: (projectId: string) =>
      request<ProjectChapter[]>(`/api/v1/projects/${projectId}/chapters`),
    syncProjectChapters: (projectId: string) =>
      request<ProjectChapter[]>(`/api/v1/projects/${projectId}/chapters/sync-outline`, {
        method: "POST",
      }),
    updateProjectChapter: (
      projectId: string,
      chapterId: string,
      payload: ProjectChapterUpdate,
    ) =>
      request<ProjectChapter>(`/api/v1/projects/${projectId}/chapters/${chapterId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    archiveProject: (id: string) =>
      request<Project>(`/api/v1/projects/${id}/archive`, {
        method: "POST",
      }),
    restoreProject: (id: string) =>
      request<Project>(`/api/v1/projects/${id}/restore`, {
        method: "POST",
      }),
    deleteProject: (id: string) =>
      request<void>(`/api/v1/projects/${id}`, {
        method: "DELETE",
      }),
    createNovelWorkflow: (payload: NovelWorkflowCreatePayload) =>
      request<NovelWorkflowListItem>("/api/v1/novel-workflows", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getNovelWorkflowStatus: (id: string) =>
      request<NovelWorkflowStatusSnapshot>(`/api/v1/novel-workflows/${id}/status`),
    getNovelWorkflow: (id: string) =>
      request<NovelWorkflow>(`/api/v1/novel-workflows/${id}`),
    getNovelWorkflowLogs: (id: string, offset = 0) =>
      request<NovelWorkflowLogs>(`/api/v1/novel-workflows/${id}/logs?offset=${offset}`),
    getNovelWorkflowArtifact: (id: string, artifactName: string) =>
      request<string>(`/api/v1/novel-workflows/${id}/artifacts/${artifactName}`),
    pauseNovelWorkflow: (id: string) =>
      request<NovelWorkflowStatusSnapshot>(`/api/v1/novel-workflows/${id}/pause`, {
        method: "POST",
      }),
    resumeNovelWorkflow: (id: string) =>
      request<NovelWorkflowStatusSnapshot>(`/api/v1/novel-workflows/${id}/resume`, {
        method: "POST",
      }),
    decideNovelWorkflow: (id: string, payload: NovelWorkflowDecisionPayload) =>
      request<NovelWorkflowStatusSnapshot>(`/api/v1/novel-workflows/${id}/decision`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    waitForNovelWorkflow: pollNovelWorkflow,
    generateConcepts: async (payload: ConceptGeneratePayload, options?: RegenerateOptions) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "concept_bootstrap",
        ...payload,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload);
      const markdown = await request<string>(`/api/v1/novel-workflows/${run.id}/artifacts/concepts_markdown`);
      return parseMarkdownConcepts(markdown);
    },
    getStyleAnalysisJobs: (params?: { offset?: number; limit?: number }) => {
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<StyleAnalysisJobListItem[]>(
        `/api/v1/style-analysis-jobs?offset=${offset}&limit=${limit}`
      );
    },
    getStyleAnalysisJobStatus: (id: string) =>
      request<StyleAnalysisJobStatusSnapshot>(`/api/v1/style-analysis-jobs/${id}/status`),
    getStyleAnalysisJob: (id: string) =>
      request<StyleAnalysisJob>(`/api/v1/style-analysis-jobs/${id}`),
    getStyleAnalysisJobLogs: (id: string, offset = 0) =>
      request<StyleAnalysisJobLogs>(`/api/v1/style-analysis-jobs/${id}/logs?offset=${offset}`),
    getStyleAnalysisJobAnalysisMeta: (id: string) =>
      request<AnalysisMeta>(`/api/v1/style-analysis-jobs/${id}/analysis-meta`),
    getStyleAnalysisJobAnalysisReport: (id: string) =>
      request<AnalysisReportMarkdown>(`/api/v1/style-analysis-jobs/${id}/analysis-report`),
    getStyleAnalysisJobVoiceProfile: (id: string) =>
      request<VoiceProfileMarkdown>(`/api/v1/style-analysis-jobs/${id}/voice-profile`),
    resumeStyleAnalysisJob: (id: string) =>
      request<StyleAnalysisJobStatusSnapshot>(`/api/v1/style-analysis-jobs/${id}/resume`, {
        method: "POST",
      }),
    pauseStyleAnalysisJob: (id: string) =>
      request<StyleAnalysisJobStatusSnapshot>(`/api/v1/style-analysis-jobs/${id}/pause`, {
        method: "POST",
      }),
    deleteStyleAnalysisJob: (id: string) =>
      request<void>(`/api/v1/style-analysis-jobs/${id}`, {
        method: "DELETE",
      }),
    createStyleAnalysisJob: (payload: StyleAnalysisJobCreatePayload & { file: File }) => {
      const formData = new FormData();
      formData.append("style_name", payload.style_name);
      formData.append("provider_id", payload.provider_id);
      if (payload.model) {
        formData.append("model", payload.model);
      }
      formData.append("file", payload.file);

      return request<StyleAnalysisJobListItem>("/api/v1/style-analysis-jobs", {
        method: "POST",
        body: formData,
      });
    },
    getStyleProfiles: (params?: { offset?: number; limit?: number }) => {
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<StyleProfileListItem[]>(
        `/api/v1/style-profiles?offset=${offset}&limit=${limit}`
      );
    },
    getStyleProfile: (id: string) => request<StyleProfile>(`/api/v1/style-profiles/${id}`),
    createStyleProfile: (payload: StyleProfileCreatePayload) =>
      request<StyleProfile>("/api/v1/style-profiles", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updateStyleProfile: (id: string, payload: StyleProfileUpdatePayload) =>
      request<StyleProfile>(`/api/v1/style-profiles/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    deleteStyleProfile: (id: string) =>
      request<void>(`/api/v1/style-profiles/${id}`, {
        method: "DELETE",
      }),
    getPlotAnalysisJobs: (params?: { offset?: number; limit?: number }) => {
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<PlotAnalysisJobListItem[]>(
        `/api/v1/plot-analysis-jobs?offset=${offset}&limit=${limit}`
      );
    },
    getPlotAnalysisJobStatus: (id: string) =>
      request<PlotAnalysisJobStatusSnapshot>(`/api/v1/plot-analysis-jobs/${id}/status`),
    getPlotAnalysisJob: (id: string) =>
      request<PlotAnalysisJob>(`/api/v1/plot-analysis-jobs/${id}`),
    getPlotAnalysisJobLogs: (id: string, offset = 0) =>
      request<PlotAnalysisJobLogs>(`/api/v1/plot-analysis-jobs/${id}/logs?offset=${offset}`),
    getPlotAnalysisJobAnalysisMeta: (id: string) =>
      request<PlotAnalysisMeta>(`/api/v1/plot-analysis-jobs/${id}/analysis-meta`),
    getPlotAnalysisJobAnalysisReport: (id: string) =>
      request<PlotAnalysisReportMarkdown>(`/api/v1/plot-analysis-jobs/${id}/analysis-report`),
    getPlotAnalysisJobPlotSkeleton: (id: string) =>
      request<PlotSkeletonMarkdown>(`/api/v1/plot-analysis-jobs/${id}/plot-skeleton`),
    getPlotAnalysisJobStoryEngine: (id: string) =>
      request<StoryEngineMarkdown>(`/api/v1/plot-analysis-jobs/${id}/story-engine`),
    resumePlotAnalysisJob: (id: string) =>
      request<PlotAnalysisJobStatusSnapshot>(`/api/v1/plot-analysis-jobs/${id}/resume`, {
        method: "POST",
      }),
    pausePlotAnalysisJob: (id: string) =>
      request<PlotAnalysisJobStatusSnapshot>(`/api/v1/plot-analysis-jobs/${id}/pause`, {
        method: "POST",
      }),
    deletePlotAnalysisJob: (id: string) =>
      request<void>(`/api/v1/plot-analysis-jobs/${id}`, {
        method: "DELETE",
      }),
    createPlotAnalysisJob: (payload: PlotAnalysisJobCreatePayload & { file: File }) => {
      const formData = new FormData();
      formData.append("plot_name", payload.plot_name);
      formData.append("provider_id", payload.provider_id);
      if (payload.model) {
        formData.append("model", payload.model);
      }
      formData.append("file", payload.file);

      return request<PlotAnalysisJobListItem>("/api/v1/plot-analysis-jobs", {
        method: "POST",
        body: formData,
      });
    },
    getPlotProfiles: (params?: { offset?: number; limit?: number }) => {
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<PlotProfileListItem[]>(
        `/api/v1/plot-profiles?offset=${offset}&limit=${limit}`
      );
    },
    getPlotProfile: (id: string) => request<PlotProfile>(`/api/v1/plot-profiles/${id}`),
    createPlotProfile: (payload: PlotProfileCreatePayload) =>
      request<PlotProfile>("/api/v1/plot-profiles", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updatePlotProfile: (id: string, payload: PlotProfileUpdatePayload) =>
      request<PlotProfile>(`/api/v1/plot-profiles/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    deletePlotProfile: (id: string) =>
      request<void>(`/api/v1/plot-profiles/${id}`, {
        method: "DELETE",
      }),
    runContinuationWorkflow: async (
      projectId: string,
      textBeforeCursor: string,
      currentChapterContext = "",
      previousChapterContext = "",
      totalContentLength = 0,
      generationProfile?: GenerationProfile | null,
    ) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "continuation_write",
        project_id: projectId,
        text_before_cursor: textBeforeCursor,
        current_chapter_context: currentChapterContext,
        previous_chapter_context: previousChapterContext,
        total_content_length: totalContentLength,
        ...(generationProfile ? { generation_profile: generationProfile } : {}),
      } as NovelWorkflowCreatePayload);
      const markdown = await request<string>(`/api/v1/novel-workflows/${run.id}/artifacts/prose_markdown`);
      return buildSseResponse(markdown);
    },
    proposeBibleUpdate: async (
      projectId: string,
      currentCharactersStatus: string,
      currentRuntimeState: string,
      currentRuntimeThreads: string,
      contentToCheck: string,
      syncScope: "generated_fragment" | "chapter_full",
      options?: RegenerateOptions,
    ) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "memory_refresh",
        project_id: projectId,
        content_to_check: contentToCheck,
        sync_scope: syncScope,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload);
      const markdown = await request<string>(`/api/v1/novel-workflows/${run.id}/artifacts/memory_update_bundle`);
      const chapterSummary = syncScope === "chapter_full"
        ? await request<string>(`/api/v1/novel-workflows/${run.id}/artifacts/chapter_summary_markdown`).catch(() => "")
        : "";
      const parsed = parseMemoryBundle(markdown);
      return {
        proposed_characters_status: parsed.proposedCharactersStatus,
        proposed_runtime_state: parsed.proposedRuntimeState,
        proposed_runtime_threads: parsed.proposedRuntimeThreads,
        proposed_summary: chapterSummary || null,
        changed:
          parsed.proposedCharactersStatus !== currentCharactersStatus
          || parsed.proposedRuntimeState !== currentRuntimeState
          || parsed.proposedRuntimeThreads !== currentRuntimeThreads
          || Boolean(chapterSummary),
      } satisfies NovelMemoryWorkflowResult;
    },
    runBeatsWorkflow: async (
      projectId: string,
      textBeforeCursor: string,
      runtimeState: string,
      runtimeThreads: string,
      outlineDetail: string,
      currentChapterContext?: string,
      previousChapterContext?: string,
      totalContentLength = 0,
      options?: RegenerateOptions,
    ) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "beats_generate",
        project_id: projectId,
        text_before_cursor: textBeforeCursor,
        current_chapter_context: currentChapterContext ?? "",
        previous_chapter_context: previousChapterContext ?? "",
        total_content_length: totalContentLength,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload);
      const markdown = await request<string>(`/api/v1/novel-workflows/${run.id}/artifacts/beats_markdown`);
      return {
        beats: markdown.split(/\r?\n/).map((line) => line.trim()).filter(Boolean),
      } satisfies NovelBeatWorkflowResult;
    },
    runBeatExpandWorkflow: async (
      projectId: string,
      textBeforeCursor: string,
      runtimeState: string,
      runtimeThreads: string,
      outlineDetail: string,
      beat: string,
      beatIndex: number,
      totalBeats: number,
      precedingBeatsProse: string,
      currentChapterContext?: string,
      previousChapterContext?: string,
      options?: RegenerateOptions,
    ) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "beat_expand",
        project_id: projectId,
        text_before_cursor: textBeforeCursor,
        beat,
        beat_index: beatIndex,
        total_beats: totalBeats,
        preceding_beats_prose: precedingBeatsProse,
        current_chapter_context: currentChapterContext ?? "",
        previous_chapter_context: previousChapterContext ?? "",
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload);
      const markdown = await request<string>(`/api/v1/novel-workflows/${run.id}/artifacts/prose_markdown`);
      return buildSseResponse(markdown);
    },
    runProjectBootstrapWorkflow: (projectId: string) =>
      createNovelWorkflowAndWait({
        intent_type: "project_bootstrap",
        project_id: projectId,
      } as NovelWorkflowCreatePayload),
    runSectionWorkflow: (
      projectId: string,
      payload: {
        section: string;
        description?: string;
        world_building?: string;
        characters_blueprint?: string;
        outline_master?: string;
        outline_detail?: string;
        characters_status?: string;
        runtime_state?: string;
        runtime_threads?: string;
      },
      options?: RegenerateOptions,
    ) =>
      createNovelWorkflowAndWait({
        intent_type: "section_generate",
        project_id: projectId,
        section: payload.section,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload).then(async ({ run }) => {
        const markdown = await request<string>(`/api/v1/novel-workflows/${run.id}/artifacts/section_markdown`);
        return buildSseResponse(markdown);
      }),
    streamNovelWorkflowArtifact: async (runId: string, artifactName: string) => {
      const status = await pollNovelWorkflow(runId);
      if (status.status === "failed") {
        throw new Error(status.error_message || "工作流执行失败");
      }
      const markdown = await request<string>(`/api/v1/novel-workflows/${runId}/artifacts/${artifactName}`);
      return buildSseResponse(markdown);
    },
    runVolumeWorkflow: (projectId: string, options?: RegenerateOptions) =>
      createNovelWorkflowAndWait({
        intent_type: "volume_generate",
        project_id: projectId,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload).then(async ({ run }) => {
        const markdown = await request<string>(`/api/v1/novel-workflows/${run.id}/artifacts/volumes_markdown`);
        return buildSseResponse(markdown);
      }),
    runVolumeChaptersWorkflow: (
      projectId: string,
      volumeIndex: number,
      options?: RegenerateOptions,
    ) =>
      createNovelWorkflowAndWait({
        intent_type: "volume_chapters_generate",
        project_id: projectId,
        volume_index: volumeIndex,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload).then(async ({ run }) => {
        const markdown = await request<string>(`/api/v1/novel-workflows/${run.id}/artifacts/volume_chapters_markdown`);
        return buildSseResponse(markdown);
      }),
  };
}
