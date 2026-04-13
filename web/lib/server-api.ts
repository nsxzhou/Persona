import "server-only";

import { cookies } from "next/headers";

import type {
  User,
  Project,
  ProviderConfig,
  StyleProfile,
  StyleProfileListItem,
  ProjectPayload,
} from "@/lib/types";
import { createJsonRequester } from "@/lib/api/transport";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type SetupStatus = {
  initialized: boolean;
};

async function getServerRequester() {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();
  return createJsonRequester({
    baseUrl: API_BASE_URL,
    defaultInit: {
      cache: "no-store",
      credentials: "include",
      headers: cookieHeader ? { cookie: cookieHeader } : undefined,
    },
  });
}

export async function getServerSetupStatus(): Promise<SetupStatus> {
  const req = await getServerRequester();
  return req<SetupStatus>("/api/v1/setup/status");
}

export async function getServerCurrentUser(): Promise<User | null> {
  const req = await getServerRequester();
  try {
    return await req<User>("/api/v1/me");
  } catch (error: any) {
    if (
      error.message.includes("401") ||
      error.message.includes("未登录") ||
      error.message.includes("登录状态已失效") ||
      error.message.includes("Unauthorized")
    ) {
      return null;
    }
    throw error;
  }
}

export async function getServerProject(id: string): Promise<Project> {
  const req = await getServerRequester();
  return req<Project>(`/api/v1/projects/${id}`);
}

export async function getServerProviderConfigs(): Promise<ProviderConfig[]> {
  const req = await getServerRequester();
  return req<ProviderConfig[]>("/api/v1/provider-configs");
}

export async function getServerStyleProfiles(limit = 100): Promise<StyleProfileListItem[]> {
  const req = await getServerRequester();
  return req<StyleProfileListItem[]>(`/api/v1/style-profiles?limit=${limit}`);
}

export async function getServerStyleProfile(id: string): Promise<StyleProfile> {
  const req = await getServerRequester();
  return req<StyleProfile>(`/api/v1/style-profiles/${id}`);
}

export async function createServerProject(payload: ProjectPayload): Promise<Project> {
  const req = await getServerRequester();
  return req<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateServerProject(id: string, payload: Partial<ProjectPayload>): Promise<Project> {
  const req = await getServerRequester();
  return req<Project>(`/api/v1/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
