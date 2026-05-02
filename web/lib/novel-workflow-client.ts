import type { Requester } from "@/lib/api/requester";
import {
  buildSseResponse,
  parseMarkdownConcepts,
  parseMemoryBundle,
} from "@/lib/workflow-artifacts";
import type {
  ConceptGeneratePayload,
  GenerationProfile,
  NovelBeatWorkflowResult,
  NovelMemoryWorkflowResult,
  NovelWorkflowCreatePayload,
  NovelWorkflowListItem,
  NovelWorkflowStatusSnapshot,
} from "@/lib/types";

export type RegenerateOptions = {
  previousOutput?: string;
  userFeedback?: string;
};

export function parseBeatsMarkdown(markdown: string): string[] {
  const beats: string[] = [];
  let sawExplicitBeat = false;

  for (const rawLine of markdown.split(/\r?\n/)) {
    const line = rawLine.trim().replace(/^\uFEFF/, "");
    if (!line) continue;
    if (/^```/.test(line) || /^>/.test(line) || /^#{1,6}\s+/.test(line)) continue;
    if (/^(?:-{3,}|={3,}|\*{3,}|·{3,}|…{3,})$/.test(line)) continue;
    if (/^(?:以下是|如下|下面是|接下来是|节拍如下|节拍列表|生成如下|请生成|请看|说明：|备注：|提示：)/.test(line)) {
      continue;
    }

    const stripped = line.replace(
      /^\s*(?:[-*+•]\s*|(?:\d+|[一二三四五六七八九十]+)[.)、]\s*)/,
      "",
    ).trim();
    if (!stripped) continue;

    const square = stripped.match(/^\[(?<label>[^\]\n]{1,80})\]\s*(?<body>.+?)\s*$/u);
    const fullwidth = stripped.match(/^【(?<label>[^】\n]{1,80})】\s*(?<body>.+?)\s*$/u);
    const normalized = square
      ? `[${square.groups?.label?.trim() ?? ""}] ${square.groups?.body?.trim() ?? ""}`
      : fullwidth
        ? `[${fullwidth.groups?.label?.trim() ?? ""}] ${fullwidth.groups?.body?.trim() ?? ""}`
        : stripped;
    if (!normalized) continue;

    if (normalized.startsWith("[")) {
      sawExplicitBeat = true;
    }
    beats.push(normalized);
  }

  if (sawExplicitBeat) {
    return beats.filter((beat) => beat.startsWith("["));
  }
  return beats;
}

export type SelectionRewriteWorkflowPayload = {
  projectId: string;
  selectedText: string;
  textBeforeSelection: string;
  textAfterSelection: string;
  rewriteInstruction: string;
  currentChapterContext?: string;
  previousChapterContext?: string;
  totalContentLength?: number;
  generationProfile?: GenerationProfile | null;
};

function regenerateFields(options?: RegenerateOptions): Record<string, string> {
  if (!options) return {};
  const out: Record<string, string> = {};
  if (options.previousOutput !== undefined && options.previousOutput !== null) {
    out.previous_output = options.previousOutput;
  }
  if (options.userFeedback !== undefined && options.userFeedback !== null) {
    out.feedback = options.userFeedback;
  }
  return out;
}

export function createNovelWorkflowClient(request: Requester) {
  const pollNovelWorkflow = async (
    runId: string,
  ): Promise<NovelWorkflowStatusSnapshot> => {
    while (true) {
      const status = await request<NovelWorkflowStatusSnapshot>(
        `/api/v1/novel-workflows/${runId}/status`,
      );
      if (
        status.status === "succeeded" ||
        status.status === "paused" ||
        status.status === "failed"
      ) {
        return status;
      }
      await new Promise((resolve) => setTimeout(resolve, 10));
    }
  };

  const createNovelWorkflowAndWait = async (
    payload: NovelWorkflowCreatePayload,
  ): Promise<{
    run: NovelWorkflowListItem;
    status: NovelWorkflowStatusSnapshot;
  }> => {
    const run = await request<NovelWorkflowListItem>("/api/v1/novel-workflows", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const status = await pollNovelWorkflow(run.id);
    if (status.status === "failed") {
      throw new Error(status.error_message || "工作流执行失败");
    }
    return { run, status };
  };

  return {
    waitForNovelWorkflow: pollNovelWorkflow,
    generateConcepts: async (
      payload: ConceptGeneratePayload,
      options?: RegenerateOptions,
    ) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "concept_bootstrap",
        ...payload,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload);
      const markdown = await request<string>(
        `/api/v1/novel-workflows/${run.id}/artifacts/concepts_markdown`,
      );
      return parseMarkdownConcepts(markdown);
    },
    runSelectionRewriteWorkflow: async ({
      projectId,
      selectedText,
      textBeforeSelection,
      textAfterSelection,
      rewriteInstruction,
      currentChapterContext = "",
      previousChapterContext = "",
      totalContentLength = 0,
      generationProfile,
    }: SelectionRewriteWorkflowPayload) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "selection_rewrite",
        project_id: projectId,
        selected_text: selectedText,
        text_before_selection: textBeforeSelection,
        text_after_selection: textAfterSelection,
        rewrite_instruction: rewriteInstruction,
        current_chapter_context: currentChapterContext,
        previous_chapter_context: previousChapterContext,
        total_content_length: totalContentLength,
        ...(generationProfile ? { generation_profile: generationProfile } : {}),
      } as NovelWorkflowCreatePayload);
      return await request<string>(
        `/api/v1/novel-workflows/${run.id}/artifacts/prose_markdown`,
      );
    },
    proposeBibleUpdate: async (
      projectId: string,
      currentCharactersStatus: string,
      currentRuntimeState: string,
      currentRuntimeThreads: string,
      contentToCheck: string,
      syncScope: "generated_fragment" | "chapter_full",
      options?: RegenerateOptions,
    ) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "memory_refresh",
        project_id: projectId,
        content_to_check: contentToCheck,
        sync_scope: syncScope,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload);
      const markdown = await request<string>(
        `/api/v1/novel-workflows/${run.id}/artifacts/memory_update_bundle`,
      );
      const chapterSummary =
        syncScope === "chapter_full"
          ? await request<string>(
              `/api/v1/novel-workflows/${run.id}/artifacts/chapter_summary_markdown`,
            ).catch(() => "")
          : "";
      const parsed = parseMemoryBundle(markdown);
      return {
        proposed_characters_status: parsed.proposedCharactersStatus,
        proposed_runtime_state: parsed.proposedRuntimeState,
        proposed_runtime_threads: parsed.proposedRuntimeThreads,
        proposed_summary: chapterSummary || null,
        changed:
          parsed.proposedCharactersStatus !== currentCharactersStatus ||
          parsed.proposedRuntimeState !== currentRuntimeState ||
          parsed.proposedRuntimeThreads !== currentRuntimeThreads ||
          Boolean(chapterSummary),
      } satisfies NovelMemoryWorkflowResult;
    },
    runBeatsWorkflow: async (
      projectId: string,
      textBeforeCursor: string,
      runtimeState: string,
      runtimeThreads: string,
      outlineDetail: string,
      currentChapterContext?: string,
      previousChapterContext?: string,
      totalContentLength = 0,
      options?: RegenerateOptions,
    ) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "beats_generate",
        project_id: projectId,
        text_before_cursor: textBeforeCursor,
        current_chapter_context: currentChapterContext ?? "",
        previous_chapter_context: previousChapterContext ?? "",
        total_content_length: totalContentLength,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload);
      const markdown = await request<string>(
        `/api/v1/novel-workflows/${run.id}/artifacts/beats_markdown`,
      );
      return {
        beats: parseBeatsMarkdown(markdown),
      } satisfies NovelBeatWorkflowResult;
    },
    runBeatExpandWorkflow: async (
      projectId: string,
      textBeforeCursor: string,
      runtimeState: string,
      runtimeThreads: string,
      outlineDetail: string,
      beat: string,
      beatIndex: number,
      totalBeats: number,
      precedingBeatsProse: string,
      currentChapterContext?: string,
      previousChapterContext?: string,
      options?: RegenerateOptions,
    ) => {
      const { run } = await createNovelWorkflowAndWait({
        intent_type: "beat_expand",
        project_id: projectId,
        text_before_cursor: textBeforeCursor,
        beat,
        beat_index: beatIndex,
        total_beats: totalBeats,
        preceding_beats_prose: precedingBeatsProse,
        current_chapter_context: currentChapterContext ?? "",
        previous_chapter_context: previousChapterContext ?? "",
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload);
      const markdown = await request<string>(
        `/api/v1/novel-workflows/${run.id}/artifacts/prose_markdown`,
      );
      return buildSseResponse(markdown);
    },
    runSectionWorkflow: (
      projectId: string,
      payload: {
        section: string;
        description?: string;
        world_building?: string;
        characters_blueprint?: string;
        outline_master?: string;
        outline_detail?: string;
        characters_status?: string;
        runtime_state?: string;
        runtime_threads?: string;
      },
      options?: RegenerateOptions,
    ) =>
      createNovelWorkflowAndWait({
        intent_type: "section_generate",
        project_id: projectId,
        section: payload.section,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload).then(async ({ run }) => {
        const markdown = await request<string>(
          `/api/v1/novel-workflows/${run.id}/artifacts/section_markdown`,
        );
        return buildSseResponse(markdown);
      }),
    streamNovelWorkflowArtifact: async (runId: string, artifactName: string) => {
      const status = await pollNovelWorkflow(runId);
      if (status.status === "failed") {
        throw new Error(status.error_message || "工作流执行失败");
      }
      const markdown = await request<string>(
        `/api/v1/novel-workflows/${runId}/artifacts/${artifactName}`,
      );
      return buildSseResponse(markdown);
    },
    runVolumeWorkflow: (projectId: string, options?: RegenerateOptions) =>
      createNovelWorkflowAndWait({
        intent_type: "volume_generate",
        project_id: projectId,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload).then(async ({ run }) => {
        const markdown = await request<string>(
          `/api/v1/novel-workflows/${run.id}/artifacts/volumes_markdown`,
        );
        return buildSseResponse(markdown);
      }),
    runVolumeChaptersWorkflow: (
      projectId: string,
      volumeIndex: number,
      options?: RegenerateOptions,
    ) =>
      createNovelWorkflowAndWait({
        intent_type: "volume_chapters_generate",
        project_id: projectId,
        volume_index: volumeIndex,
        ...regenerateFields(options),
      } as NovelWorkflowCreatePayload).then(async ({ run }) => {
        const markdown = await request<string>(
          `/api/v1/novel-workflows/${run.id}/artifacts/volume_chapters_markdown`,
        );
        return buildSseResponse(markdown);
      }),
  };
}
