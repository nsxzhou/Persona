import type {
  AnalysisMeta,
  AnalysisReportMarkdown,
  ConnectionTestResponse,
  LoginPayload,
  NovelWorkflow,
  NovelWorkflowCreatePayload,
  NovelWorkflowDecisionPayload,
  NovelWorkflowListItem,
  NovelWorkflowLogs,
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
import type { Requester } from "@/lib/api/requester";
import { createNovelWorkflowClient } from "@/lib/novel-workflow-client";

export type {
  RegenerateOptions,
  SelectionRewriteWorkflowPayload,
} from "@/lib/novel-workflow-client";

export function createApiClient(request: Requester) {
  const novelWorkflowClient = createNovelWorkflowClient(request);

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
    waitForNovelWorkflow: novelWorkflowClient.waitForNovelWorkflow,
    generateConcepts: novelWorkflowClient.generateConcepts,
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
    runSelectionRewriteWorkflow: novelWorkflowClient.runSelectionRewriteWorkflow,
    proposeBibleUpdate: novelWorkflowClient.proposeBibleUpdate,
    runBeatsWorkflow: novelWorkflowClient.runBeatsWorkflow,
    runBeatExpandWorkflow: novelWorkflowClient.runBeatExpandWorkflow,
    runSectionWorkflow: novelWorkflowClient.runSectionWorkflow,
    streamNovelWorkflowArtifact: novelWorkflowClient.streamNovelWorkflowArtifact,
    runVolumeWorkflow: novelWorkflowClient.runVolumeWorkflow,
    runVolumeChaptersWorkflow: novelWorkflowClient.runVolumeChaptersWorkflow,
  };
}
