import { describe, expect, test, vi } from "vitest";

import { createApiClient } from "@/lib/api-client";
import { createJsonRequester } from "@/lib/api/transport";
import { parseBeatsMarkdown } from "@/lib/novel-workflow-client";
import type {
  ConceptGeneratePayload,
  NovelBeatWorkflowResult,
  NovelMemoryWorkflowResult,
  PlotProfile,
  SetupResponse,
  SetupStatusResponse,
  StyleProfile,
  StyleAnalysisJobCreatePayload,
  StyleAnalysisJobStatusSnapshot,
} from "@/lib/types";

describe("API contracts", () => {
  test("api client methods align with exported OpenAPI contract types", async () => {
    const request = vi.fn(async <T,>(path: string, init?: RequestInit) => {
      if (path === "/api/v1/novel-workflows" && init?.method === "POST") {
        const payload = JSON.parse(String(init.body ?? "{}")) as { intent_type?: string };
        return {
          id: `${payload.intent_type ?? "workflow"}-1`,
          intent_type: payload.intent_type ?? "section_generate",
          project_id: "project-1",
          chapter_id: null,
          provider_id: null,
          model_name: null,
          status: "pending",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: [],
          warnings: [],
          error_message: null,
          started_at: null,
          completed_at: null,
          created_at: "2026-04-27T00:00:00Z",
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.startsWith("/api/v1/novel-workflows/") && path.endsWith("/status")) {
        return {
          id: "workflow-1",
          status: "succeeded",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: ["artifact"],
          warnings: [],
          error_message: null,
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.includes("/artifacts/concepts_markdown")) {
        return "### 标题A\n简介A" as T;
      }
      if (path.includes("/artifacts/memory_update_bundle")) {
        return "## 角色动态状态\n\n角色状态\n\n## 运行时状态\n\n运行时状态\n\n## 伏笔与线索追踪\n\n伏笔" as T;
      }
      if (path.includes("/artifacts/chapter_summary_markdown")) {
        return "章节摘要" as T;
      }
      if (path.includes("/artifacts/beats_markdown")) {
        return "生成如下：\n- 【平静→疑惑】 发现脚印\n- 【震惊→决然】 他推门而入" as T;
      }
      if (path.includes("/artifacts/prose_markdown")) {
        return "正文内容" as T;
      }
      if (path.includes("/artifacts/section_markdown")) {
        return "区块内容" as T;
      }
      if (path.includes("/artifacts/volumes_markdown")) {
        return "卷结构" as T;
      }
      if (path.includes("/artifacts/volume_chapters_markdown")) {
        return "章节结构" as T;
      }
      return undefined as T;
    }) as unknown as {
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
    const beatsPromise: Promise<NovelBeatWorkflowResult> = client.runBeatsWorkflow(
      "project-1",
      "",
      "",
      "",
      "",
    );
    const biblePromise: Promise<NovelMemoryWorkflowResult> = client.proposeBibleUpdate(
      "project-1",
      "",
      "",
      "",
      "new content",
      "generated_fragment",
    );
    const styleProfileCreatePromise: Promise<StyleProfile> = client.createStyleProfile({
      job_id: "style-job-1",
      style_name: "冷白风",
      voice_profile_markdown: "# Voice Profile\n## 3.1 口头禅与常用表达\n- 短句推进\n",
    });
    const styleProfileUpdatePromise: Promise<StyleProfile> = client.updateStyleProfile("style-profile-1", {
      style_name: "冷白风终版",
      voice_profile_markdown: "# Voice Profile\n## 3.1 口头禅与常用表达\n- 更碎的短句推进\n",
    });
    const plotProfileCreatePromise: Promise<PlotProfile> = client.createPlotProfile({
      job_id: "plot-job-1",
      plot_name: "反派修罗场",
      story_engine_markdown: "# Plot Writing Guide\n## Core Plot Formula\n- 用压力迫使主角行动。\n",
    });
    const plotProfileUpdatePromise: Promise<PlotProfile> = client.updatePlotProfile("plot-profile-1", {
      plot_name: "反派修罗场终版",
      story_engine_markdown: "# Plot Writing Guide\n## Core Plot Formula\n- 制造主动选择。\n",
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
    expect(parseBeatsMarkdown("节拍如下：\n- 【平静→疑惑】 发现脚印\n- 旁白说明")).toEqual([
      "[平静→疑惑] 发现脚印",
    ]);
  });

  test("concept generation payload accepts selected profile ids", async () => {
    const request = vi.fn(async <T,>(path: string, init?: RequestInit) => {
      if (path === "/api/v1/novel-workflows") {
        return {
          id: "concept-bootstrap-1",
          intent_type: "concept_bootstrap",
          project_id: null,
          chapter_id: null,
          provider_id: "provider-1",
          model_name: null,
          status: "pending",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: [],
          warnings: [],
          error_message: null,
          started_at: null,
          completed_at: null,
          created_at: "2026-04-27T00:00:00Z",
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.endsWith("/status")) {
        return {
          id: "concept-bootstrap-1",
          status: "succeeded",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: ["concepts_markdown"],
          warnings: [],
          error_message: null,
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.includes("/artifacts/concepts_markdown")) {
        return "### 标题A\n简介A" as T;
      }
      return undefined as T;
    }) as unknown as {
      <T>(path: string, init?: RequestInit): Promise<T>;
      raw: (path: string, init?: RequestInit) => Promise<Response>;
    };
    request.raw = vi.fn(async () => new Response(null, { status: 204 }));
    const client = createApiClient(request);
    const payload: ConceptGeneratePayload = {
      inspiration: "一个被迫冒名顶替入局的寒门书生。",
      provider_id: "provider-1",
      model_name: "gpt-4.1-mini",
      count: 3,
      generation_profile: {
        target_market: "mainstream",
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

    const createCall = (request as unknown as { mock: { calls: Array<[string, RequestInit?]> } }).mock.calls.find(
      ([path, init]) => path === "/api/v1/novel-workflows" && init?.method === "POST",
    );
    expect(createCall).toBeDefined();
    const [, createInit] = createCall!;
    const body = JSON.parse(String(createInit?.body ?? "{}")) as Record<string, unknown>;

    expect(body).toEqual({
      intent_type: "concept_bootstrap",
      ...payload,
    });
    expect(body).toHaveProperty("model_name", "gpt-4.1-mini");
    expect(body).not.toHaveProperty("model");
    expect(request).toHaveBeenCalledWith(
      "/api/v1/novel-workflows",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(body),
      }),
    );
  });

  test("concept generation ignores assistant preamble and parses numbered cards", async () => {
    const markdown = `好的，作为资深策划编辑，我已根据你的反馈完成修订。

---

### 1. 给我砸了
简介一第一段。

简介一第二段。

### 2、系统逼我做坏人，但怎么惩罚你
简介二，不能吞掉第三张卡。

### 3 等我报复完，你再告诉她好不好
简介三。`;
    const request = vi.fn(async <T,>(path: string, init?: RequestInit) => {
      if (path === "/api/v1/novel-workflows" && init?.method === "POST") {
        return {
          id: "concept-bootstrap-1",
          intent_type: "concept_bootstrap",
          project_id: null,
          chapter_id: null,
          provider_id: "provider-1",
          model_name: null,
          status: "pending",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: [],
          warnings: [],
          error_message: null,
          started_at: null,
          completed_at: null,
          created_at: "2026-04-27T00:00:00Z",
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.endsWith("/status")) {
        return {
          id: "concept-bootstrap-1",
          status: "succeeded",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: ["concepts_markdown"],
          warnings: [],
          error_message: null,
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.includes("/artifacts/concepts_markdown")) {
        return markdown as T;
      }
      return undefined as T;
    }) as unknown as {
      <T>(path: string, init?: RequestInit): Promise<T>;
      raw: (path: string, init?: RequestInit) => Promise<Response>;
    };
    request.raw = vi.fn(async () => new Response(null, { status: 204 }));
    const client = createApiClient(request);

    const result = await client.generateConcepts({
      inspiration: "庄子昂被系统惩罚续命。",
      provider_id: "provider-1",
      count: 3,
      generation_profile: null,
      style_profile_id: null,
      plot_profile_id: null,
    });

    expect(result.concepts).toEqual([
      {
        title: "给我砸了",
        synopsis: "简介一第一段。\n\n简介一第二段。",
      },
      {
        title: "系统逼我做坏人，但怎么惩罚你",
        synopsis: "简介二，不能吞掉第三张卡。",
      },
      {
        title: "等我报复完，你再告诉她好不好",
        synopsis: "简介三。",
      },
    ]);
  });

  test("regeneration options use canonical feedback field", async () => {
    const request = vi.fn(async <T,>(path: string, init?: RequestInit) => {
      if (path === "/api/v1/novel-workflows" && init?.method === "POST") {
        const payload = JSON.parse(String(init.body ?? "{}")) as { intent_type?: string };
        return {
          id: `${payload.intent_type ?? "workflow"}-1`,
          intent_type: payload.intent_type ?? "section_generate",
          project_id: null,
          chapter_id: null,
          provider_id: null,
          model_name: null,
          status: "pending",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: [],
          warnings: [],
          error_message: null,
          started_at: null,
          completed_at: null,
          created_at: "2026-04-27T00:00:00Z",
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.endsWith("/status")) {
        return {
          id: "concept-bootstrap-1",
          status: "succeeded",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: ["concepts_markdown"],
          warnings: [],
          error_message: null,
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.includes("/artifacts/concepts_markdown")) {
        return "### 标题A\n简介A" as T;
      }
      return undefined as T;
    }) as unknown as {
      <T>(path: string, init?: RequestInit): Promise<T>;
      raw: (path: string, init?: RequestInit) => Promise<Response>;
    };
    request.raw = vi.fn(async () => new Response(null, { status: 204 }));
    const client = createApiClient(request);

    await client.generateConcepts(
      {
        inspiration: "旧灵感",
        provider_id: "provider-1",
        count: 3,
        generation_profile: null,
        style_profile_id: null,
        plot_profile_id: null,
      },
      {
        previousOutput: "上一版",
        userFeedback: "主角换名，剧情微调",
      },
    );

    const createCall = (request as unknown as { mock: { calls: Array<[string, RequestInit?]> } }).mock.calls.find(
      ([path, init]) => path === "/api/v1/novel-workflows" && init?.method === "POST",
    );
    expect(createCall).toBeDefined();
    const [, init] = createCall!;
    const body = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;

    expect(body.previous_output).toBe("上一版");
    expect(body.feedback).toBe("主角换名，剧情微调");
    expect(body).not.toHaveProperty("user_feedback");
  });

  test("proposeBibleUpdate sends content_to_check and sync_scope", async () => {
    const request = vi.fn(async <T,>(path: string, init?: RequestInit) => {
      if (path === "/api/v1/novel-workflows") {
        return {
          id: "memory-refresh-1",
          intent_type: "memory_refresh",
          project_id: "project-1",
          chapter_id: null,
          provider_id: null,
          model_name: null,
          status: "pending",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: [],
          warnings: [],
          error_message: null,
          started_at: null,
          completed_at: null,
          created_at: "2026-04-27T00:00:00Z",
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.endsWith("/status")) {
        return {
          id: "memory-refresh-1",
          status: "succeeded",
          stage: null,
          checkpoint_kind: null,
          latest_artifacts: ["memory_update_bundle"],
          warnings: [],
          error_message: null,
          updated_at: "2026-04-27T00:00:00Z",
          pause_requested_at: null,
        } as T;
      }
      if (path.includes("/artifacts/memory_update_bundle")) {
        return "## 角色动态状态\n\n角色状态\n\n## 运行时状态\n\n当前状态\n\n## 伏笔与线索追踪\n\n当前伏笔" as T;
      }
      if (path.includes("/artifacts/chapter_summary_markdown")) {
        return "章节摘要" as T;
      }
      return undefined as T;
    }) as unknown as {
      <T>(path: string, init?: RequestInit): Promise<T>;
      raw: (path: string, init?: RequestInit) => Promise<Response>;
    };
    request.raw = vi.fn(async () => new Response(null, { status: 204 }));
    const client = createApiClient(request);

    await client.proposeBibleUpdate(
      "project-1",
      "当前角色状态",
      "当前状态",
      "当前伏笔",
      "整章正文",
      "chapter_full",
    );

    expect(request).toHaveBeenCalledWith(
      "/api/v1/novel-workflows",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          intent_type: "memory_refresh",
          project_id: "project-1",
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
