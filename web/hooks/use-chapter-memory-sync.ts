import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { RegenerateOptions } from "@/lib/api-client";
import type {
  MemorySyncScope,
  MemorySyncSource,
  Project,
  ProjectChapter,
  ProjectChapterUpdate,
  ProjectPayload,
} from "@/lib/types";

const MIN_LENGTH_FOR_AUTO_SYNC = 200;

export type RuntimeUpdateDiffState = {
  open: boolean;
  currentState: string;
  proposedState: string;
  currentThreads: string;
  proposedThreads: string;
};

const EMPTY_DIFF_STATE: RuntimeUpdateDiffState = {
  open: false,
  currentState: "",
  proposedState: "",
  currentThreads: "",
  proposedThreads: "",
};

async function hashContent(content: string) {
  const encoded = new TextEncoder().encode(content);
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function getStoredDiff(
  chapter: ProjectChapter | null,
  project: Pick<Project, "runtime_state" | "runtime_threads">,
): RuntimeUpdateDiffState {
  return {
    open: false,
    currentState: project.runtime_state,
    proposedState: chapter?.memory_sync_proposed_state ?? "",
    currentThreads: project.runtime_threads ?? "",
    proposedThreads: chapter?.memory_sync_proposed_threads ?? "",
  };
}

export function useChapterMemorySync({
  projectId,
  project,
  selectedChapter,
  getCurrentContent,
  persistProjectUpdate,
  persistChapterUpdate,
}: {
  projectId: string;
  project: Pick<Project, "runtime_state" | "runtime_threads">;
  selectedChapter: ProjectChapter | null;
  getCurrentContent: () => string;
  persistProjectUpdate: (
    payload: Partial<ProjectPayload>,
    options?: { successMessage?: string; errorMessage?: string },
  ) => Promise<unknown>;
  persistChapterUpdate: (
    chapterId: string,
    payload: ProjectChapterUpdate,
  ) => Promise<ProjectChapter>;
}) {
  const [bibleDiff, setBibleDiff] = useState<RuntimeUpdateDiffState>(EMPTY_DIFF_STATE);
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    setBibleDiff(EMPTY_DIFF_STATE);
  }, [selectedChapter?.id]);

  const chapterSyncSnapshot = useMemo(
    () =>
      selectedChapter
        ? {
            status: selectedChapter.memory_sync_status,
            source: selectedChapter.memory_sync_source,
            scope: selectedChapter.memory_sync_scope,
            checkedAt: selectedChapter.memory_sync_checked_at,
            errorMessage: selectedChapter.memory_sync_error_message,
            proposedState: selectedChapter.memory_sync_proposed_state,
            proposedThreads: selectedChapter.memory_sync_proposed_threads,
          }
        : null,
    [selectedChapter],
  );

  const persistMemorySnapshot = useCallback(
    async (
      checkedChapterContent: string,
      payload: ProjectChapterUpdate,
    ) => {
      if (!selectedChapter) {
        throw new Error("未选择章节");
      }
      return persistChapterUpdate(selectedChapter.id, {
        memory_sync_checked_at: new Date().toISOString(),
        memory_sync_checked_content_hash: await hashContent(checkedChapterContent),
        ...payload,
      });
    },
    [persistChapterUpdate, selectedChapter],
  );

  const openStoredDiff = useCallback(() => {
    if (!selectedChapter || selectedChapter.memory_sync_status !== "pending_review") {
      return;
    }
    setBibleDiff({
      ...getStoredDiff(selectedChapter, project),
      open: true,
    });
  }, [project, selectedChapter]);

  const dismissRuntimeUpdate = useCallback(() => {
    setBibleDiff((prev) => ({ ...prev, open: false }));
  }, []);

  const markSyncFailed = useCallback(
    async (
      checkedChapterContent: string,
      source: MemorySyncSource,
      scope: MemorySyncScope,
      message: string,
    ) => {
      await persistMemorySnapshot(checkedChapterContent, {
        memory_sync_status: "failed",
        memory_sync_source: source,
        memory_sync_scope: scope,
        memory_sync_error_message: message,
        memory_sync_proposed_state: null,
        memory_sync_proposed_threads: null,
      });
      setBibleDiff(EMPTY_DIFF_STATE);
      toast.error("同步记忆失败");
    },
    [persistMemorySnapshot],
  );

  const syncContent = useCallback(
    async (
      contentToCheck: string,
      checkedChapterContent: string,
      source: MemorySyncSource,
      scope: MemorySyncScope,
      options?: RegenerateOptions,
    ) => {
      if (!selectedChapter) return;
      if (scope === "generated_fragment" && contentToCheck.trim().length < MIN_LENGTH_FOR_AUTO_SYNC) {
        return;
      }

      setIsChecking(true);
      try {
        const result = await api.proposeBibleUpdate(
          projectId,
          project.runtime_state,
          project.runtime_threads ?? "",
          contentToCheck,
          scope,
          options,
        );

        if (result.changed) {
          await persistMemorySnapshot(checkedChapterContent, {
            memory_sync_status: "pending_review",
            memory_sync_source: source,
            memory_sync_scope: scope,
            memory_sync_error_message: null,
            memory_sync_proposed_state: result.proposed_runtime_state,
            memory_sync_proposed_threads: result.proposed_runtime_threads,
          });
          setBibleDiff({
            open: true,
            currentState: project.runtime_state,
            proposedState: result.proposed_runtime_state,
            currentThreads: project.runtime_threads ?? "",
            proposedThreads: result.proposed_runtime_threads,
          });
          return;
        }

        await persistMemorySnapshot(checkedChapterContent, {
          memory_sync_status: "no_change",
          memory_sync_source: source,
          memory_sync_scope: scope,
          memory_sync_error_message: null,
          memory_sync_proposed_state: null,
          memory_sync_proposed_threads: null,
        });
        setBibleDiff(EMPTY_DIFF_STATE);
      } catch (error) {
        const message = error instanceof Error ? error.message : "同步记忆失败";
        await markSyncFailed(checkedChapterContent, source, scope, message);
      } finally {
        setIsChecking(false);
      }
    },
    [markSyncFailed, persistMemorySnapshot, project, projectId, selectedChapter],
  );

  const handleGeneratedContent = useCallback(
    async (generated: string) => {
      await syncContent(generated, getCurrentContent(), "auto", "generated_fragment");
    },
    [getCurrentContent, syncContent],
  );

  const handleManualSync = useCallback(
    async (checkedContent: string, options?: RegenerateOptions) => {
      await syncContent(checkedContent, checkedContent, "manual", "chapter_full", options);
    },
    [syncContent],
  );

  const handleAutoChapterSync = useCallback(
    async (content: string) => {
      if (!selectedChapter) return;
      setIsChecking(true);
      try {
        const result = await api.proposeBibleUpdate(
          projectId,
          project.runtime_state,
          project.runtime_threads ?? "",
          content,
          "chapter_full",
        );
        if (result.changed) {
          await persistProjectUpdate(
            {
              runtime_state: result.proposed_runtime_state,
              runtime_threads: result.proposed_runtime_threads,
            },
            { errorMessage: "更新运行时状态失败" },
          );
          await persistMemorySnapshot(content, {
            memory_sync_status: "synced",
            memory_sync_source: "auto",
            memory_sync_scope: "chapter_full",
            memory_sync_error_message: null,
            memory_sync_proposed_state: null,
            memory_sync_proposed_threads: null,
          });
        } else {
          await persistMemorySnapshot(content, {
            memory_sync_status: "no_change",
            memory_sync_source: "auto",
            memory_sync_scope: "chapter_full",
            memory_sync_error_message: null,
            memory_sync_proposed_state: null,
            memory_sync_proposed_threads: null,
          });
        }
        setBibleDiff(EMPTY_DIFF_STATE);
      } catch (error) {
        const message = error instanceof Error ? error.message : "自动同步失败";
        await persistMemorySnapshot(content, {
          memory_sync_status: "failed",
          memory_sync_source: "auto",
          memory_sync_scope: "chapter_full",
          memory_sync_error_message: message,
          memory_sync_proposed_state: null,
          memory_sync_proposed_threads: null,
        }).catch(() => {});
      } finally {
        setIsChecking(false);
      }
    },
    [
      persistMemorySnapshot,
      persistProjectUpdate,
      project.runtime_state,
      project.runtime_threads,
      projectId,
      selectedChapter,
    ],
  );

  const acceptRuntimeUpdate = useCallback(
    async (state: string, threads: string) => {
      if (!selectedChapter) return;
      await persistProjectUpdate(
        { runtime_state: state, runtime_threads: threads },
        {
          successMessage: "运行时状态已更新",
          errorMessage: "更新运行时状态失败",
        },
      );
      await persistMemorySnapshot(getCurrentContent(), {
        memory_sync_status: "synced",
        memory_sync_source: selectedChapter.memory_sync_source ?? "manual",
        memory_sync_scope: selectedChapter.memory_sync_scope ?? "chapter_full",
        memory_sync_error_message: null,
        memory_sync_proposed_state: null,
        memory_sync_proposed_threads: null,
      });
      setBibleDiff(EMPTY_DIFF_STATE);
    },
    [getCurrentContent, persistMemorySnapshot, persistProjectUpdate, selectedChapter],
  );

  return {
    bibleDiff,
    isChecking,
    chapterSyncSnapshot,
    handleGeneratedContent,
    handleManualSync,
    handleAutoChapterSync,
    markSyncFailed,
    openStoredDiff,
    acceptRuntimeUpdate,
    dismissRuntimeUpdate,
  };
}
