import type {
  LoginPayload,
  Project,
  ProjectPayload,
  ProviderConfig,
  ProviderPayload,
  SetupPayload,
  User,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: "请求失败" }));
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
};

