import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type {
  ChapterRewriteBatch,
  ChapterRewriteBatchItem,
  ChapterRewriteBatchListItem,
  ProjectChapter,
} from "@/lib/types";
import { chapterRewriteBatchKeys, isBatchActive, markBatchItemsApplied } from "./helpers";

type ApplyState = Record<string, "applying" | "failed">;

export function useChapterRewriteApplyActions({
  batch,
  batchItems,
  isApplying,
  onApplied,
  projectId,
  queryClient,
  setActiveChapterId,
  setActiveBatchId,
  setApplyStateByItemId,
  clearArtifacts,
}: {
  batch: ChapterRewriteBatch | null;
  batchItems: ChapterRewriteBatchItem[];
  isApplying: boolean;
  onApplied: (chapter: ProjectChapter) => void;
  projectId: string;
  queryClient: QueryClient;
  setActiveChapterId: (chapterId: string | null) => void;
  setActiveBatchId: (batchId: string | null) => void;
  setApplyStateByItemId: Dispatch<SetStateAction<ApplyState>>;
  clearArtifacts: () => void;
}) {
  const applyOne = useCallback(async (chapterId: string) => {
    if (!batch || isBatchActive(batch) || isApplying) return null;
    const item = batchItems.find((candidate) => candidate.chapter_id === chapterId);
    if (!item || item.status !== "generated") return null;
    setApplyStateByItemId((current) => ({ ...current, [item.id]: "applying" }));
    setActiveChapterId(chapterId);
    try {
      const result = await api.applyChapterRewriteBatchItem(batch.id, item.id);
      onApplied(result.chapter);
      const appliedIds = new Set([item.id]);
      queryClient.setQueryData<ChapterRewriteBatch>(
        chapterRewriteBatchKeys.detail(batch.id),
        (current) => current ? markBatchItemsApplied(current, appliedIds) : current,
      );
      queryClient.setQueryData<ChapterRewriteBatchListItem[]>(
        chapterRewriteBatchKeys.list(projectId),
        (current) =>
          current?.map((candidate) =>
            candidate.id === batch.id
              ? markBatchItemsApplied(candidate, appliedIds)
              : candidate,
          ),
      );
      queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.detail(batch.id) });
      queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.list(projectId) });
      if (batch.total_count === batch.applied_count + 1) {
        setActiveBatchId(null);
        clearArtifacts();
      }
      setApplyStateByItemId((current) => {
        const next = { ...current };
        delete next[item.id];
        return next;
      });
      toast.success("章节正文已替换");
      return result.chapter;
    } catch (error) {
      setApplyStateByItemId((current) => ({ ...current, [item.id]: "failed" }));
      toast.error(error instanceof Error ? error.message : "应用改写失败");
      return null;
    }
  }, [
    batch,
    batchItems,
    clearArtifacts,
    isApplying,
    onApplied,
    projectId,
    queryClient,
    setActiveBatchId,
    setActiveChapterId,
    setApplyStateByItemId,
  ]);

  const applyAll = useCallback(async () => {
    if (!batch || isBatchActive(batch) || isApplying) return;
    const generated = batchItems.filter((item) => item.status === "generated");
    if (generated.length === 0) {
      toast.message("没有可应用的改写预览");
      return;
    }
    setApplyStateByItemId((current) => ({
      ...current,
      ...Object.fromEntries(generated.map((item) => [item.id, "applying" as const])),
    }));
    try {
      const result = await api.applyChapterRewriteBatch(batch.id);
      for (const applied of result.applied) {
        onApplied(applied.chapter);
      }
      const appliedIds = new Set(generated.map((item) => item.id));
      queryClient.setQueryData<ChapterRewriteBatch>(
        chapterRewriteBatchKeys.detail(batch.id),
        (current) => current ? markBatchItemsApplied(current, appliedIds) : current,
      );
      queryClient.setQueryData<ChapterRewriteBatchListItem[]>(
        chapterRewriteBatchKeys.list(projectId),
        (current) =>
          current?.map((candidate) =>
            candidate.id === batch.id
              ? markBatchItemsApplied(candidate, appliedIds)
              : candidate,
          ),
      );
      await queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.detail(batch.id) });
      await queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.list(projectId) });
      setActiveBatchId(null);
      clearArtifacts();
      setApplyStateByItemId({});
      toast.success(`批量应用完成：成功 ${result.applied.length} 章`);
    } catch (error) {
      setApplyStateByItemId({});
      toast.error(error instanceof Error ? error.message : "批量应用失败");
    }
  }, [
    batch,
    batchItems,
    clearArtifacts,
    isApplying,
    onApplied,
    projectId,
    queryClient,
    setActiveBatchId,
    setApplyStateByItemId,
  ]);

  return { applyOne, applyAll };
}
