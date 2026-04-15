import type {
  AnalysisMeta,
  AnalysisReportMarkdown,
  ConceptGeneratePayload,
  ConceptGenerateResult,
  LoginPayload,
  PromptPackMarkdown,
  Project,
  ProjectPayload,
  ProviderConfig,
  ProviderPayload,
  SetupPayload,
  StyleAnalysisJob,
  StyleAnalysisJobListItem,
  StyleAnalysisJobLogs,
  StyleProfile,
  StyleProfileCreatePayload,
  StyleProfileListItem,
  StyleSummaryMarkdown,
  StyleProfileUpdatePayload,
  User,
} from "@/lib/types";

type StyleAnalysisJobStatus = Pick<
  StyleAnalysisJob,
  "id" | "status" | "stage" | "error_message" | "updated_at"
>;

type Requester = {
  <T>(path: string, init?: RequestInit): Promise<T>;
  raw: (path: string, init?: RequestInit) => Promise<Response>;
};

export function createApiClient(request: Requester) {
  return {
    getSetupStatus: () => request<{ initialized: boolean }>("/api/v1/setup/status"),
    setup: (payload: SetupPayload) =>
      request<{ user: User; provider: ProviderConfig }>("/api/v1/setup", {
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
      request<{ status: string; message: string }>(`/api/v1/provider-configs/${id}/test`, {
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
      return request<Project[]>(
        `/api/v1/projects?include_archived=${includeArchived}&offset=${offset}&limit=${limit}`
      );
    },
    getProject: (id: string) => request<Project>(`/api/v1/projects/${id}`),
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
    generateConcepts: (payload: ConceptGeneratePayload) =>
      request<ConceptGenerateResult>("/api/v1/projects/generate-concepts", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getStyleAnalysisJobs: (params?: { offset?: number; limit?: number }) => {
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<StyleAnalysisJobListItem[]>(
        `/api/v1/style-analysis-jobs?offset=${offset}&limit=${limit}`
      );
    },
    getStyleAnalysisJobStatus: (id: string) =>
      request<StyleAnalysisJobStatus>(`/api/v1/style-analysis-jobs/${id}/status`),
    getStyleAnalysisJob: (id: string) =>
      request<StyleAnalysisJob>(`/api/v1/style-analysis-jobs/${id}`),
    getStyleAnalysisJobLogs: (id: string, offset = 0) =>
      request<StyleAnalysisJobLogs>(`/api/v1/style-analysis-jobs/${id}/logs?offset=${offset}`),
    getStyleAnalysisJobAnalysisMeta: (id: string) =>
      request<AnalysisMeta>(`/api/v1/style-analysis-jobs/${id}/analysis-meta`),
    getStyleAnalysisJobAnalysisReport: (id: string) =>
      request<AnalysisReportMarkdown>(`/api/v1/style-analysis-jobs/${id}/analysis-report`),
    getStyleAnalysisJobStyleSummary: (id: string) =>
      request<StyleSummaryMarkdown>(`/api/v1/style-analysis-jobs/${id}/style-summary`),
    getStyleAnalysisJobPromptPack: (id: string) =>
      request<PromptPackMarkdown>(`/api/v1/style-analysis-jobs/${id}/prompt-pack`),
    resumeStyleAnalysisJob: (id: string) =>
      request<StyleAnalysisJobStatus>(`/api/v1/style-analysis-jobs/${id}/resume`, {
        method: "POST",
      }),
    pauseStyleAnalysisJob: (id: string) =>
      request<StyleAnalysisJobStatus>(`/api/v1/style-analysis-jobs/${id}/pause`, {
        method: "POST",
      }),
    deleteStyleAnalysisJob: (id: string) =>
      request<void>(`/api/v1/style-analysis-jobs/${id}`, {
        method: "DELETE",
      }),
    createStyleAnalysisJob: (payload: {
      style_name: string;
      provider_id: string;
      model?: string;
      file: File;
    }) => {
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
        // Omit Content-Type to let the browser set it with the boundary
        headers: {
          "Content-Type": undefined as any,
        },
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
      request<StyleProfileListItem>("/api/v1/style-profiles", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updateStyleProfile: (id: string, payload: StyleProfileUpdatePayload) =>
      request<StyleProfileListItem>(`/api/v1/style-profiles/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    deleteStyleProfile: (id: string) =>
      request<void>(`/api/v1/style-profiles/${id}`, {
        method: "DELETE",
      }),
    completeEditor: (projectId: string, textBeforeCursor: string) =>
      request.raw(`/api/v1/projects/${projectId}/editor/complete`, {
        method: "POST",
        body: JSON.stringify({ text_before_cursor: textBeforeCursor }),
      }),
    proposeBibleUpdate: (projectId: string, currentBible: string, newContentContext: string) =>
      request<{ proposed_bible: string }>(`/api/v1/projects/${projectId}/editor/propose-bible-update`, {
        method: "POST",
        body: JSON.stringify({
          current_bible: currentBible,
          new_content_context: newContentContext,
        }),
      }),
    generateBeats: (projectId: string, textBeforeCursor: string, storyBible: string, outlineDetail: string) =>
      request<{ beats: string[] }>(`/api/v1/projects/${projectId}/editor/generate-beats`, {
        method: "POST",
        body: JSON.stringify({
          text_before_cursor: textBeforeCursor,
          story_bible: storyBible,
          outline_detail: outlineDetail,
        }),
      }),
    expandBeat: (
      projectId: string,
      textBeforeCursor: string,
      storyBible: string,
      outlineDetail: string,
      beat: string,
      beatIndex: number,
      totalBeats: number,
      precedingBeatsProse: string
    ) =>
      request.raw(`/api/v1/projects/${projectId}/editor/expand-beat`, {
        method: "POST",
        body: JSON.stringify({
          text_before_cursor: textBeforeCursor,
          story_bible: storyBible,
          outline_detail: outlineDetail,
          beat,
          beat_index: beatIndex,
          total_beats: totalBeats,
          preceding_beats_prose: precedingBeatsProse,
        }),
      }),
    generateSection: (projectId: string, payload: Record<string, string>) =>
      request.raw(`/api/v1/projects/${projectId}/editor/generate-section`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  };
}
