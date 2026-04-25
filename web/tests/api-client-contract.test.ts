import { describe, expect, test, vi } from "vitest";

import { createApiClient } from "@/lib/api-client";
import { createJsonRequester } from "@/lib/api/transport";
import type {
  BeatGenerateResponse,
  BibleUpdateResponse,
  ConceptGeneratePayload,
  PlotProfile,
  SetupResponse,
  SetupStatusResponse,
  StyleProfile,
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
      "generated_fragment",
    );
    const styleProfileCreatePromise: Promise<StyleProfile> = client.createStyleProfile({
      job_id: "style-job-1",
      style_name: "冷白风",
      voice_profile_markdown: "# Voice Profile\n## sentence_rhythm\n- 短句推进\n",
    });
    const styleProfileUpdatePromise: Promise<StyleProfile> = client.updateStyleProfile("style-profile-1", {
      style_name: "冷白风终版",
      voice_profile_markdown: "# Voice Profile\n## sentence_rhythm\n- 更碎的短句推进\n",
    });
    const plotProfileCreatePromise: Promise<PlotProfile> = client.createPlotProfile({
      job_id: "plot-job-1",
      plot_name: "反派修罗场",
      story_engine_markdown: "# Story Engine Profile\n## genre_mother\n- xianxia\n",
    });
    const plotProfileUpdatePromise: Promise<PlotProfile> = client.updatePlotProfile("plot-profile-1", {
      plot_name: "反派修罗场终版",
      story_engine_markdown: "# Story Engine Profile\n## genre_mother\n- urban\n",
    });

    const payload: StyleAnalysisJobCreatePayload = {
      style_name: "冷白风",
      provider_id: "provider-1",
      model: "gpt-4.1-mini",
      file: new File(["sample"], "sample.txt", { type: "text/plain" }),
    };
    void client.createStyleAnalysisJob(payload);

    await Promise.all([
      setupStatusPromise,
      setupPromise,
      statusPromise,
      beatsPromise,
      biblePromise,
      styleProfileCreatePromise,
      styleProfileUpdatePromise,
      plotProfileCreatePromise,
      plotProfileUpdatePromise,
    ]);
    expect(request).toHaveBeenCalled();
  });

  test("concept generation payload accepts selected profile ids", async () => {
    const request = vi.fn(async <T,>(_path: string) => ({ concepts: [] }) as T) as unknown as {
      <T>(path: string, init?: RequestInit): Promise<T>;
      raw: (path: string, init?: RequestInit) => Promise<Response>;
    };
    request.raw = vi.fn(async () => new Response(null, { status: 204 }));
    const client = createApiClient(request);
    const payload: ConceptGeneratePayload = {
      inspiration: "一个被迫冒名顶替入局的寒门书生。",
      provider_id: "provider-1",
      model: null,
      count: 3,
      generation_profile: {
        genre_mother: "xianxia",
        desire_overlays: ["harem_collect"],
        intensity_level: "explicit",
        pov_mode: "limited_third",
        morality_axis: "ruthless_growth",
        pace_density: "fast",
      },
      style_profile_id: "style-1",
      plot_profile_id: "plot-1",
    };

    await client.generateConcepts(payload);

    expect(request).toHaveBeenCalledWith(
      "/api/v1/projects/generate-concepts",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      }),
    );
  });

  test("proposeBibleUpdate sends content_to_check and sync_scope", async () => {
    const request = vi.fn(async <T,>(_path: string) => undefined as T) as unknown as {
      <T>(path: string, init?: RequestInit): Promise<T>;
      raw: (path: string, init?: RequestInit) => Promise<Response>;
    };
    request.raw = vi.fn(async () => new Response(null, { status: 204 }));
    const client = createApiClient(request);

    await client.proposeBibleUpdate(
      "project-1",
      "当前状态",
      "当前伏笔",
      "整章正文",
      "chapter_full",
    );

    expect(request).toHaveBeenCalledWith(
      "/api/v1/projects/project-1/editor/propose-bible-update",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          current_runtime_state: "当前状态",
          current_runtime_threads: "当前伏笔",
          content_to_check: "整章正文",
          sync_scope: "chapter_full",
        }),
      }),
    );
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
