import type {
  AnalysisMeta,
  AnalysisReportMarkdown,
  ChapterRewriteBatch,
  ChapterRewriteBatchApplyItemResponse,
  ChapterRewriteBatchApplyResponse,
  ChapterRewriteBatchCreatePayload,
  ChapterRewriteBatchListItem,
  ChapterRewriteBatchLogs,
  ConnectionTestResponse,
  LoginPayload,
  NovelWorkflow,
  NovelWorkflowCreatePayload,
  NovelWorkflowDecisionPayload,
  NovelWorkflowListItem,
  NovelWorkflowLogs,
  NovelWorkflowStatusSnapshot,
  NovelChapterRewriteJob,
  NovelChapterRewriteJobApplyResponse,
  NovelChapterRewriteJobCreatePayload,
  NovelChapterRewriteJobLogs,
  NovelChapterRewriteJobStatus,
  NovelImportCommitResponse,
  NovelImportCreatePayload,
  NovelImportPreview,
  NovelImportUpdatePayload,
  Project,
  SetupResponse,
  SetupStatusResponse,
  ProjectChapter,
  ProjectChapterUpdate,
  ProjectPayload,
  ProjectPromptAsset,
  ProjectPromptAssetApplySuggestionsRequest,
  ProjectPromptAssetApplySuggestionsResponse,
  ProjectPromptAssetCreate,
  ProjectPromptAssetUpdate,
  PromptStackPreviewRequest,
  PromptStackPreviewResponse,
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
  ProviderChatTestRequest,
  ProviderChatTestResponse,
  ProviderConfigUpdatePayload,
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
    updateProviderConfig: (id: string, payload: ProviderConfigUpdatePayload) =>
      request<ProviderConfig>(`/api/v1/provider-configs/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    testProviderConfig: (id: string) =>
      request<ConnectionTestResponse>(`/api/v1/provider-configs/${id}/test`, {
        method: "POST",
      }),
    chatTestProviderConfig: (id: string, payload: ProviderChatTestRequest) =>
      request<ProviderChatTestResponse>(`/api/v1/provider-configs/${id}/chat-test`, {
        method: "POST",
        body: JSON.stringify(payload),
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
    getProjectPromptAssets: (projectId: string) =>
      request<ProjectPromptAsset[]>(`/api/v1/projects/${projectId}/prompt-assets`),
    createProjectPromptAsset: (projectId: string, payload: ProjectPromptAssetCreate) =>
      request<ProjectPromptAsset>(`/api/v1/projects/${projectId}/prompt-assets`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updateProjectPromptAsset: (
      projectId: string,
      assetId: string,
      payload: ProjectPromptAssetUpdate,
    ) =>
      request<ProjectPromptAsset>(`/api/v1/projects/${projectId}/prompt-assets/${assetId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    deleteProjectPromptAsset: (projectId: string, assetId: string) =>
      request<void>(`/api/v1/projects/${projectId}/prompt-assets/${assetId}`, {
        method: "DELETE",
      }),
    applyProjectPromptAssetSuggestions: (
      projectId: string,
      payload: ProjectPromptAssetApplySuggestionsRequest,
    ) =>
      request<ProjectPromptAssetApplySuggestionsResponse>(
        `/api/v1/projects/${projectId}/prompt-assets/apply-suggestions`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      ),
    previewProjectPromptStack: (projectId: string, payload: PromptStackPreviewRequest) =>
      request<PromptStackPreviewResponse>(`/api/v1/projects/${projectId}/prompt-stack/preview`, {
        method: "POST",
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
    previewNovelImport: (payload: NovelImportCreatePayload) => {
      const formData = new FormData();
      formData.append("project_name", payload.project_name);
      formData.append("default_provider_id", payload.default_provider_id);
      if (payload.default_model) formData.append("default_model", payload.default_model);
      if (payload.style_profile_id) formData.append("style_profile_id", payload.style_profile_id);
      if (payload.plot_profile_id) formData.append("plot_profile_id", payload.plot_profile_id);
      if (payload.generation_profile) {
        formData.append("generation_profile", JSON.stringify(payload.generation_profile));
      }
      formData.append("rights_confirmed", String(payload.rights_confirmed));
      formData.append("file", payload.file);

      return request<NovelImportPreview>("/api/v1/novel-imports/preview", {
        method: "POST",
        body: formData,
      });
    },
    updateNovelImport: (draftId: string, payload: NovelImportUpdatePayload) =>
      request<NovelImportPreview>(`/api/v1/novel-imports/${draftId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    commitNovelImport: (draftId: string) =>
      request<NovelImportCommitResponse>(`/api/v1/novel-imports/${draftId}/commit`, {
        method: "POST",
      }),
    createNovelChapterRewriteJob: (payload: NovelChapterRewriteJobCreatePayload) =>
      request<NovelChapterRewriteJob>("/api/v1/novel-chapter-rewrite-jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getNovelChapterRewriteJobStatus: (id: string) =>
      request<NovelChapterRewriteJobStatus>(`/api/v1/novel-chapter-rewrite-jobs/${id}/status`),
    getNovelChapterRewriteJobLogs: (id: string, offset = 0) =>
      request<NovelChapterRewriteJobLogs>(
        `/api/v1/novel-chapter-rewrite-jobs/${id}/logs?offset=${offset}`,
      ),
    getNovelChapterRewriteJobArtifact: (id: string) =>
      request<string>(`/api/v1/novel-chapter-rewrite-jobs/${id}/artifact`),
    applyNovelChapterRewriteJob: (id: string) =>
      request<NovelChapterRewriteJobApplyResponse>(
        `/api/v1/novel-chapter-rewrite-jobs/${id}/apply`,
        {
          method: "POST",
        },
      ),
    createChapterRewriteBatch: (payload: ChapterRewriteBatchCreatePayload) =>
      request<ChapterRewriteBatch>("/api/v1/chapter-rewrite-batches", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getChapterRewriteBatches: (params?: {
      projectId?: string | null;
      offset?: number;
      limit?: number;
    }) => {
      const query = new URLSearchParams();
      if (params?.projectId) query.set("project_id", params.projectId);
      query.set("offset", String(params?.offset ?? 0));
      query.set("limit", String(params?.limit ?? 50));
      return request<ChapterRewriteBatchListItem[]>(
        `/api/v1/chapter-rewrite-batches?${query.toString()}`,
      );
    },
    getChapterRewriteBatch: (id: string) =>
      request<ChapterRewriteBatch>(`/api/v1/chapter-rewrite-batches/${id}`),
    getChapterRewriteBatchItemLogs: (batchId: string, itemId: string, offset = 0) =>
      request<ChapterRewriteBatchLogs>(
        `/api/v1/chapter-rewrite-batches/${batchId}/items/${itemId}/logs?offset=${offset}`,
      ),
    getChapterRewriteBatchItemArtifact: (batchId: string, itemId: string) =>
      request<string>(`/api/v1/chapter-rewrite-batches/${batchId}/items/${itemId}/artifact`),
    applyChapterRewriteBatchItem: (batchId: string, itemId: string) =>
      request<ChapterRewriteBatchApplyItemResponse>(
        `/api/v1/chapter-rewrite-batches/${batchId}/items/${itemId}/apply`,
        { method: "POST" },
      ),
    applyChapterRewriteBatch: (batchId: string) =>
      request<ChapterRewriteBatchApplyResponse>(
        `/api/v1/chapter-rewrite-batches/${batchId}/apply`,
        { method: "POST" },
      ),
    listNovelWorkflows: (params?: {
      projectId?: string | null;
      intentType?: NovelWorkflowCreatePayload["intent_type"] | null;
      status?: NovelWorkflowListItem["status"] | null;
      offset?: number;
      limit?: number;
    }) => {
      const query = new URLSearchParams();
      if (params?.projectId) query.set("project_id", params.projectId);
      if (params?.intentType) query.set("intent_type", params.intentType);
      if (params?.status) query.set("status", params.status);
      query.set("offset", String(params?.offset ?? 0));
      query.set("limit", String(params?.limit ?? 50));
      return request<NovelWorkflowListItem[]>(`/api/v1/novel-workflows?${query.toString()}`);
    },
    createNovelWorkflow: (payload: NovelWorkflowCreatePayload) =>
      request<NovelWorkflowListItem>("/api/v1/novel-workflows", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    clearNovelWorkflowHistory: () =>
      request<void>("/api/v1/novel-workflows", {
        method: "DELETE",
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
    runChapterExpandWorkflow: novelWorkflowClient.runChapterExpandWorkflow,
    runSectionWorkflow: novelWorkflowClient.runSectionWorkflow,
    streamNovelWorkflowArtifact: novelWorkflowClient.streamNovelWorkflowArtifact,
    runVolumeWorkflow: novelWorkflowClient.runVolumeWorkflow,
    runVolumeChaptersWorkflow: novelWorkflowClient.runVolumeChaptersWorkflow,
  };
}
