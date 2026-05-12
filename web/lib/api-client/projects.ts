import type { Requester } from "@/lib/api/requester";
import type {
  Project,
  ProjectBible,
  ProjectBibleUpdate,
  ProjectChapter,
  ProjectChapterUpdate,
  ProjectPayload,
  ProjectPromptAsset,
  ProjectPromptAssetApplySuggestionsRequest,
  ProjectPromptAssetApplySuggestionsResponse,
  ProjectPromptAssetCreate,
  ProjectPromptAssetUpdate,
  ProjectSummary,
  ProjectUpdatePayload,
  PromptStackPreviewRequest,
  PromptStackPreviewResponse,
} from "@/lib/types";

export function createProjectApiClient(request: Requester) {
  return {
    getProjects: (params?: { includeArchived?: boolean; offset?: number; limit?: number }) => {
      const includeArchived = params?.includeArchived ?? false;
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<ProjectSummary[]>(
        `/api/v1/projects?include_archived=${includeArchived}&offset=${offset}&limit=${limit}`,
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
  };
}
