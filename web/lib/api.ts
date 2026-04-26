import { createJsonRequester } from "@/lib/api/transport";
import { createApiClient } from "./api-client";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const request = createJsonRequester({
  baseUrl: API_BASE_URL,
  defaultInit: { credentials: "include", cache: "no-store" },
});

export const api = createApiClient(request);
