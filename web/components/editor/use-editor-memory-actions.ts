import { useCallback } from "react";
import { toast } from "sonner";
import type { StoreApi } from "zustand";

import type { RegenerateOptions } from "@/lib/api-client";
import type { MemorySyncScope, MemorySyncSource, ProjectChapter } from "@/lib/types";

import type { EditorState } from "./editor-store";

type ChapterSyncSnapshot = {
  status: ProjectChapter["memory_sync_status"];
  source: ProjectChapter["memory_sync_source"];
  scope: ProjectChapter["memory_sync_scope"];
  checkedAt: ProjectChapter["memory_sync_checked_at"];
  errorMessage: ProjectChapter["memory_sync_error_message"];
  proposedState: ProjectChapter["memory_sync_proposed_state"];
  proposedThreads: ProjectChapter["memory_sync_proposed_threads"];
  proposedSummary: ProjectChapter["memory_sync_proposed_summary"];
} | null;

export function toMemorySyncButtonSnapshot(chapterSyncSnapshot: ChapterSyncSnapshot) {
  return chapterSyncSnapshot
    ? {
        status: chapterSyncSnapshot.status ?? null,
        source: chapterSyncSnapshot.source ?? null,
        checkedAt: chapterSyncSnapshot.checkedAt ?? null,
        errorMessage: chapterSyncSnapshot.errorMessage ?? null,
      }
    : null;
}

export function useEditorMemoryActions({
  store,
  selectedChapter,
  chapterSyncSnapshot,
  saveNow,
  handleManualSync,
  markSyncFailed,
  openStoredDiff,
}: {
  store: StoreApi<EditorState>;
  selectedChapter: ProjectChapter | null;
  chapterSyncSnapshot: ChapterSyncSnapshot;
  saveNow: (nextContent: string) => Promise<ProjectChapter>;
  handleManualSync: (checkedContent: string, options?: RegenerateOptions) => Promise<void>;
  markSyncFailed: (
    checkedChapterContent: string,
    source: MemorySyncSource,
    scope: MemorySyncScope,
    message: string,
  ) => Promise<void>;
  openStoredDiff: () => void;
}) {
  const saveCurrentChapterForSync = useCallback(async () => {
    const content = store.getState().content;
    const savedChapterContent = store.getState().savedChapterContent;
    const hasUnsavedChanges = content !== savedChapterContent;
    if (!hasUnsavedChanges) {
      return content;
    }
    try {
      const savedChapter = await saveNow(content);
      return savedChapter.content;
    } catch {
      await markSyncFailed(content, "manual", "chapter_full", "保存失败，无法同步记忆");
      return null;
    }
  }, [markSyncFailed, saveNow, store]);

  const handleManualMemorySync = useCallback(async () => {
    if (!selectedChapter) return;
    const content = store.getState().content;
    const savedChapterContent = store.getState().savedChapterContent;

    const hasUnsavedChanges = content !== savedChapterContent;
    if (
      !hasUnsavedChanges &&
      selectedChapter.memory_sync_status === "pending_review" &&
      (selectedChapter.memory_sync_proposed_state !== null ||
        selectedChapter.memory_sync_proposed_threads !== null)
    ) {
      openStoredDiff();
      return;
    }

    if (
      !hasUnsavedChanges &&
      (selectedChapter.memory_sync_status === "synced" ||
        selectedChapter.memory_sync_status === "no_change")
    ) {
      toast.message("当前保存内容已检查，可使用“强制重跑”重新分析");
      return;
    }

    const checkedContent = await saveCurrentChapterForSync();
    if (checkedContent === null) return;
    await handleManualSync(checkedContent);
  }, [
    handleManualSync,
    openStoredDiff,
    saveCurrentChapterForSync,
    selectedChapter,
    store,
  ]);

  const handleForceMemorySync = useCallback(async () => {
    if (!selectedChapter) return;
    const checkedContent = await saveCurrentChapterForSync();
    if (checkedContent === null) return;
    await handleManualSync(checkedContent);
  }, [handleManualSync, saveCurrentChapterForSync, selectedChapter]);

  const handleRetryMemoryProposal = useCallback(
    async (feedback: string) => {
      if (!selectedChapter) return;
      const checkedContent = await saveCurrentChapterForSync();
      if (checkedContent === null) return;
      const previousOutput = selectedChapter.memory_sync_proposed_state
        || selectedChapter.memory_sync_proposed_threads
        ? JSON.stringify({
            runtime_state: selectedChapter.memory_sync_proposed_state ?? "",
            runtime_threads: selectedChapter.memory_sync_proposed_threads ?? "",
          })
        : undefined;
      await handleManualSync(checkedContent, {
        previousOutput,
        userFeedback: feedback || undefined,
      });
    },
    [handleManualSync, saveCurrentChapterForSync, selectedChapter],
  );

  return {
    memorySyncButtonSnapshot: toMemorySyncButtonSnapshot(chapterSyncSnapshot),
    handleManualMemorySync,
    handleForceMemorySync,
    handleRetryMemoryProposal,
  };
}
