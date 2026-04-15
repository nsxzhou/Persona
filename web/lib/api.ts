import { createJsonRequester } from "@/lib/api/transport";
import { createApiClient } from "./api-client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const request = createJsonRequester({
  baseUrl: API_BASE_URL,
  defaultInit: { credentials: "include" },
});

export const api = createApiClient(request);
