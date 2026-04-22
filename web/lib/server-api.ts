import "server-only";

import { cookies } from "next/headers";
import { createJsonRequester } from "@/lib/api/transport";
import { createApiClient } from "./api-client";
import { User } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

export async function getServerApi() {
  const req = await getServerRequester();
  return createApiClient(req);
}

export async function getServerCurrentUser(): Promise<User | null> {
  const api = await getServerApi();
  try {
    return await api.getCurrentUser();
  } catch (error: unknown) {
    if (
      typeof error === "object" &&
      error !== null &&
      "status" in error &&
      (error as { status?: unknown }).status === 401
    ) {
      return null;
    }
    throw error;
  }
}
