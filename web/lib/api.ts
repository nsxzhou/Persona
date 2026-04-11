import type {
  AnalysisMeta,
  AnalysisReport,
  LoginPayload,
  PromptPack,
  Project,
  ProjectPayload,
  ProviderConfig,
  ProviderPayload,
  SetupPayload,
  StyleAnalysisJob,
  StyleAnalysisJobListItem,
  StyleProfile,
  StyleProfileCreatePayload,
  StyleProfileListItem,
  StyleProfileUpdatePayload,
  StyleSummary,
  User,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? undefined);
  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers,
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text || response.statusText || "请求失败" };
    }
    throw new Error(data.detail ?? "请求失败");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
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
  updateProviderConfig: (id: string, payload: ProviderPayload) =>
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
  getProjects: (includeArchived: boolean) =>
    request<Project[]>(`/api/v1/projects?include_archived=${includeArchived}`),
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
  getStyleAnalysisJobs: (params?: { offset?: number; limit?: number }) => {
    const offset = params?.offset ?? 0;
    const limit = params?.limit ?? 50;
    return request<StyleAnalysisJobListItem[]>(
      `/api/v1/style-analysis-jobs?offset=${offset}&limit=${limit}`
    );
  },
  getStyleAnalysisJob: (id: string) =>
    request<StyleAnalysisJob>(`/api/v1/style-analysis-jobs/${id}`),
  getStyleAnalysisJobAnalysisMeta: (id: string) =>
    request<AnalysisMeta>(`/api/v1/style-analysis-jobs/${id}/analysis-meta`),
  getStyleAnalysisJobAnalysisReport: (id: string) =>
    request<AnalysisReport>(`/api/v1/style-analysis-jobs/${id}/analysis-report`),
  getStyleAnalysisJobStyleSummary: (id: string) =>
    request<StyleSummary>(`/api/v1/style-analysis-jobs/${id}/style-summary`),
  getStyleAnalysisJobPromptPack: (id: string) =>
    request<PromptPack>(`/api/v1/style-analysis-jobs/${id}/prompt-pack`),
  createStyleAnalysisJob: (payload: {
    style_name: string;
    provider_id: string;
    model?: string;
    file: File;
  }) => {
    const formData = new FormData();
    formData.set("style_name", payload.style_name);
    formData.set("provider_id", payload.provider_id);
    if (payload.model) {
      formData.set("model", payload.model);
    }
    formData.set("file", payload.file);
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
};
