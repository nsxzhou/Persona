import type {
  AnalysisMeta,
  AnalysisReportMarkdown,
  BeatGenerateResponse,
  BibleUpdateResponse,
  ConnectionTestResponse,
  ConceptGeneratePayload,
  ConceptGenerateResult,
  GenerationProfile,
  LoginPayload,
  Project,
  SetupResponse,
  SetupStatusResponse,
  ProjectChapter,
  ProjectChapterUpdate,
  ProjectPayload,
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
    out.user_feedback = options.userFeedback;
  }
  return out;
}

export function createApiClient(request: Requester) {
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
    updateProject: (id: string, payload: Partial<ProjectPayload>) =>
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
    generateConcepts: (payload: ConceptGeneratePayload, options?: RegenerateOptions) =>
      request<ConceptGenerateResult>("/api/v1/projects/generate-concepts", {
        method: "POST",
        body: JSON.stringify({ ...payload, ...regenerateFields(options) }),
      }),
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
    completeEditor: (
      projectId: string,
      textBeforeCursor: string,
      currentChapterContext = "",
      previousChapterContext = "",
      totalContentLength = 0,
      generationProfile?: GenerationProfile | null,
    ) =>
      request.raw(`/api/v1/projects/${projectId}/editor/complete`, {
        method: "POST",
        body: JSON.stringify({
          text_before_cursor: textBeforeCursor,
          current_chapter_context: currentChapterContext,
          previous_chapter_context: previousChapterContext,
          total_content_length: totalContentLength,
          ...(generationProfile ? { generation_profile: generationProfile } : {}),
        }),
      }),
    proposeBibleUpdate: (
      projectId: string,
      currentRuntimeState: string,
      currentRuntimeThreads: string,
      contentToCheck: string,
      syncScope: "generated_fragment" | "chapter_full",
      options?: RegenerateOptions,
    ) =>
      request<BibleUpdateResponse>(`/api/v1/projects/${projectId}/editor/propose-bible-update`, {
        method: "POST",
        body: JSON.stringify({
          current_runtime_state: currentRuntimeState,
          current_runtime_threads: currentRuntimeThreads,
          content_to_check: contentToCheck,
          sync_scope: syncScope,
          ...regenerateFields(options),
        }),
      }),
    generateBeats: (
      projectId: string,
      textBeforeCursor: string,
      runtimeState: string,
      runtimeThreads: string,
      outlineDetail: string,
      currentChapterContext?: string,
      previousChapterContext?: string,
      totalContentLength = 0,
      options?: RegenerateOptions,
    ) =>
      request<BeatGenerateResponse>(`/api/v1/projects/${projectId}/editor/generate-beats`, {
        method: "POST",
        body: JSON.stringify({
          text_before_cursor: textBeforeCursor,
          runtime_state: runtimeState,
          runtime_threads: runtimeThreads,
          outline_detail: outlineDetail,
          ...(currentChapterContext ? { current_chapter_context: currentChapterContext } : {}),
          ...(previousChapterContext ? { previous_chapter_context: previousChapterContext } : {}),
          total_content_length: totalContentLength,
          ...regenerateFields(options),
        }),
      }),
    expandBeat: (
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
    ) =>
      request.raw(`/api/v1/projects/${projectId}/editor/expand-beat`, {
        method: "POST",
        body: JSON.stringify({
          text_before_cursor: textBeforeCursor,
          runtime_state: runtimeState,
          runtime_threads: runtimeThreads,
          outline_detail: outlineDetail,
          beat,
          beat_index: beatIndex,
          total_beats: totalBeats,
          preceding_beats_prose: precedingBeatsProse,
          ...(currentChapterContext ? { current_chapter_context: currentChapterContext } : {}),
          ...(previousChapterContext ? { previous_chapter_context: previousChapterContext } : {}),
          ...regenerateFields(options),
        }),
      }),
    generateSection: (
      projectId: string,
      payload: Record<string, string>,
      options?: RegenerateOptions,
    ) =>
      request.raw(`/api/v1/projects/${projectId}/editor/generate-section`, {
        method: "POST",
        body: JSON.stringify({ ...payload, ...regenerateFields(options) }),
      }),
    generateVolumes: (projectId: string, options?: RegenerateOptions) =>
      request.raw(`/api/v1/projects/${projectId}/editor/generate-volumes`, {
        method: "POST",
        body: JSON.stringify(regenerateFields(options)),
      }),
    generateVolumeChapters: (
      projectId: string,
      volumeIndex: number,
      options?: RegenerateOptions,
    ) =>
      request.raw(`/api/v1/projects/${projectId}/editor/generate-volume-chapters`, {
        method: "POST",
        body: JSON.stringify({ volume_index: volumeIndex, ...regenerateFields(options) }),
      }),
  };
}
