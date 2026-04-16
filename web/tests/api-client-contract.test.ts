import { describe, expect, test, vi } from "vitest";

import { createApiClient } from "@/lib/api-client";
import { createJsonRequester } from "@/lib/api/transport";
import type {
  BeatGenerateResponse,
  BibleUpdateResponse,
  SetupResponse,
  SetupStatusResponse,
  StyleAnalysisJobCreatePayload,
  StyleAnalysisJobStatusSnapshot,
} from "@/lib/types";

describe("API contracts", () => {
  test("api client methods align with exported OpenAPI contract types", async () => {
    const request = vi.fn(async <T,>(_path: string) => undefined as T) as unknown as {
      <T>(path: string, init?: RequestInit): Promise<T>;
      raw: (path: string, init?: RequestInit) => Promise<Response>;
    };
    request.raw = vi.fn(async () => new Response(null, { status: 204 }));

    const client = createApiClient(request);

    const setupStatusPromise: Promise<SetupStatusResponse> = client.getSetupStatus();
    const setupPromise: Promise<SetupResponse> = client.setup({
      username: "user",
      password: "password123",
      provider: {
        label: "Primary",
        base_url: "https://api.openai.com/v1",
        api_key: "sk-test",
        default_model: "gpt-4.1-mini",
        is_enabled: true,
      },
    });
    const statusPromise: Promise<StyleAnalysisJobStatusSnapshot> = client.getStyleAnalysisJobStatus("job-1");
    const beatsPromise: Promise<BeatGenerateResponse> = client.generateBeats(
      "project-1",
      "",
      "",
      "",
      "",
    );
    const biblePromise: Promise<BibleUpdateResponse> = client.proposeBibleUpdate(
      "project-1",
      "",
      "",
      "new content",
    );

    const payload: StyleAnalysisJobCreatePayload = {
      style_name: "冷白风",
      provider_id: "provider-1",
      model: "gpt-4.1-mini",
      file: new File(["sample"], "sample.txt", { type: "text/plain" }),
    };
    void client.createStyleAnalysisJob(payload);

    await Promise.all([setupStatusPromise, setupPromise, statusPromise, beatsPromise, biblePromise]);
    expect(request).toHaveBeenCalled();
  });

  test("style analysis create payload accepts a browser File directly", () => {
    const payload: StyleAnalysisJobCreatePayload = {
      style_name: "冷白风",
      provider_id: "provider-1",
      file: new File(["sample"], "sample.txt", { type: "text/plain" }),
    };

    expect(payload.file).toBeInstanceOf(File);
  });

  test("json requester omits undefined header values for form data", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const request = createJsonRequester({ baseUrl: "http://localhost:3000" });
    const formData = new FormData();
    formData.append("file", new File(["a"], "a.txt", { type: "text/plain" }));

    await request("/upload", {
      method: "POST",
      body: formData,
      headers: { "Content-Type": undefined } as unknown as HeadersInit,
    });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(headers.has("Content-Type")).toBe(false);
  });
});
