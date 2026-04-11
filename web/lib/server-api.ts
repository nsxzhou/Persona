import "server-only";

import { cookies } from "next/headers";

import type { User } from "@/lib/types";
import { parseApiErrorDetail } from "@/lib/request-error";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type SetupStatus = {
  initialized: boolean;
};

async function requestFromServer(path: string): Promise<Response> {
  const cookieStore = await cookies();
  const headers = new Headers();
  const cookieHeader = cookieStore.toString();
  if (cookieHeader) {
    headers.set("cookie", cookieHeader);
  }

  return fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    credentials: "include",
    headers,
  });
}

async function readError(response: Response): Promise<string> {
  const text = await response.text();
  return parseApiErrorDetail(text, response.statusText || "请求失败");
}

export async function getServerSetupStatus(): Promise<SetupStatus> {
  const response = await requestFromServer("/api/v1/setup/status");
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<SetupStatus>;
}

export async function getServerCurrentUser(): Promise<User | null> {
  const response = await requestFromServer("/api/v1/me");
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<User>;
}
