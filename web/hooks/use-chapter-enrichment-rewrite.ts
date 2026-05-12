import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { ProjectChapter } from "@/lib/types";
import { useChapterRewriteApplyActions } from "@/hooks/chapter-enrichment-rewrite/use-apply-actions";
import { useChapterRewriteArtifacts } from "@/hooks/chapter-enrichment-rewrite/use-artifacts";
import { useChapterRewriteBatchQueries } from "@/hooks/chapter-enrichment-rewrite/use-batch-queries";
import {
  buildDisplayItem,
  buildFallbackChapter,
  chapterRewriteBatchKeys,
  isBatchActionable,
  isBatchActive,
  sortChapters,
} from "@/hooks/chapter-enrichment-rewrite/helpers";
import type { ChapterRewriteItem } from "@/hooks/chapter-enrichment-rewrite/types";

export type { ChapterRewriteItem, ChapterRewriteState } from "@/hooks/chapter-enrichment-rewrite/types";

export function useChapterEnrichmentRewrite({
  projectId,
  chapters,
  selectedChapter,
  onApplied,
}: {
  projectId: string;
  chapters: ProjectChapter[];
  selectedChapter: ProjectChapter | null;
  onApplied: (chapter: ProjectChapter) => void;
}) {
  const queryClient = useQueryClient();
  const orderedChapters = useMemo(() => sortChapters(chapters), [chapters]);
  const chaptersById = useMemo(
    () => new Map(orderedChapters.map((chapter) => [chapter.id, chapter])),
    [orderedChapters],
  );
  const [isOpen, setIsOpen] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [activeChapterId, setActiveChapterId] = useState<string | null>(null);
  const [selectedChapterIds, setSelectedChapterIds] = useState<Set<string>>(new Set());
  const [expansionRatioPercent, setExpansionRatioPercent] = useState(20);
  const [applyStateByItemId, setApplyStateByItemId] = useState<Record<string, "applying" | "failed">>({});
  const { batch, batchItems } = useChapterRewriteBatchQueries({
    projectId,
    activeBatchId,
    setActiveBatchId,
  });
  const isRunning = Boolean(batch && isBatchActive(batch));
  const isApplying = Object.values(applyStateByItemId).some((state) => state === "applying");

  const activeItemId = useMemo(() => {
    if (!batch) return null;
    const active = activeChapterId
      ? batchItems.find((item) => item.chapter_id === activeChapterId)
      : null;
    return active?.id ?? batchItems[0]?.id ?? null;
  }, [activeChapterId, batch, batchItems]);

  const { previews, logsByItemId, clearArtifacts } = useChapterRewriteArtifacts({
    batch,
    batchItems,
    activeItemId,
  });

  useEffect(() => {
    if (!batch || isOpen || isBatchActionable(batch)) return;
    setActiveBatchId(null);
    clearArtifacts();
    setApplyStateByItemId({});
  }, [batch, clearArtifacts, isOpen]);

  useEffect(() => {
    if (!batch) return;
    setInstruction(batch.instruction);
    setExpansionRatioPercent(batch.expansion_ratio_percent);
    setSelectedChapterIds(new Set(batchItems.map((item) => item.chapter_id)));
    const selectedChapterInBatch =
      selectedChapter && batchItems.some((item) => item.chapter_id === selectedChapter.id)
        ? selectedChapter.id
        : null;
    const currentId =
      selectedChapterInBatch ||
      batch.current_chapter_id ||
      batchItems.find((item) => item.status === "generated")?.chapter_id ||
      batchItems[0]?.chapter_id ||
      null;
    setActiveChapterId((current) =>
      current && batchItems.some((item) => item.chapter_id === current) ? current : currentId,
    );
  }, [batch, batchItems, selectedChapter]);

  const createMutation = useMutation({
    mutationFn: (payload: { chapterIds: string[]; instruction: string; expansionRatioPercent: number }) =>
      api.createChapterRewriteBatch({
        project_id: projectId,
        chapter_ids: payload.chapterIds,
        instruction: payload.instruction,
        expansion_ratio_percent: payload.expansionRatioPercent,
      }),
    onSuccess: (created) => {
      setActiveBatchId(created.id);
      setIsOpen(true);
      clearArtifacts();
      setApplyStateByItemId({});
      queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.list(projectId) });
      queryClient.setQueryData(chapterRewriteBatchKeys.detail(created.id), created);
      toast.success("章节改写任务已创建");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "创建章节改写任务失败");
    },
  });

  const openRewrite = useCallback((options?: {
    selectCurrentChapter?: boolean;
    preserveInstruction?: boolean;
  }) => {
    if (orderedChapters.length === 0) {
      toast.message("请先导入或同步章节");
      return;
    }
    if (batch && isBatchActionable(batch)) {
      const selectedChapterInBatch =
        selectedChapter && batchItems.some((item) => item.chapter_id === selectedChapter.id)
          ? selectedChapter.id
          : null;
      setActiveChapterId(
        selectedChapterInBatch ||
        batch.current_chapter_id ||
        batchItems.find((item) => item.status === "generated")?.chapter_id ||
        batchItems[0]?.chapter_id ||
        null,
      );
      setIsOpen(true);
      return;
    }
    if (batch && !isBatchActionable(batch)) {
      setActiveBatchId(null);
      clearArtifacts();
      setApplyStateByItemId({});
    }
    const defaultChapterId = selectedChapter?.id ?? orderedChapters[0]?.id ?? null;
    setSelectedChapterIds(
      options?.selectCurrentChapter && defaultChapterId
        ? new Set([defaultChapterId])
        : new Set(),
    );
    setActiveChapterId(defaultChapterId);
    if (!options?.preserveInstruction) {
      setInstruction("");
    }
    setExpansionRatioPercent(20);
    setIsOpen(true);
  }, [batch, batchItems, clearArtifacts, orderedChapters, selectedChapter]);

  const closeRewrite = useCallback(() => {
    setIsOpen(false);
  }, []);

  const selectChapter = useCallback((chapterId: string, checked: boolean) => {
    if (batch) return;
    const next = new Set(selectedChapterIds);
    if (checked) next.add(chapterId);
    else next.delete(chapterId);
    setSelectedChapterIds(next);
  }, [batch, selectedChapterIds]);

  const selectCurrentChapter = useCallback(() => {
    if (batch || !activeChapterId) return;
    setSelectedChapterIds(new Set([activeChapterId]));
  }, [activeChapterId, batch]);

  const selectAllChapters = useCallback(() => {
    if (batch) return;
    setSelectedChapterIds(new Set(orderedChapters.map((chapter) => chapter.id)));
  }, [batch, orderedChapters]);

  const clearSelectedChapters = useCallback(() => {
    if (batch) return;
    setSelectedChapterIds(new Set());
  }, [batch]);

  const startRewrite = useCallback(() => {
    if (createMutation.isPending || isRunning) return;
    const trimmed = instruction.trim();
    if (!trimmed) {
      toast.message("请输入改写要求");
      return;
    }
    const selected = orderedChapters.filter((chapter) => selectedChapterIds.has(chapter.id));
    if (selected.length === 0) {
      toast.message("请选择至少一个章节");
      return;
    }
    const normalizedRatio = Math.trunc(expansionRatioPercent);
    if (normalizedRatio < 1 || normalizedRatio > 100) {
      toast.message("扩写比例需在 1% 到 100% 之间");
      return;
    }
    createMutation.mutate({
      chapterIds: selected.map((chapter) => chapter.id),
      instruction: trimmed,
      expansionRatioPercent: normalizedRatio,
    });
  }, [createMutation, expansionRatioPercent, instruction, isRunning, orderedChapters, selectedChapterIds]);

  const { applyOne, applyAll } = useChapterRewriteApplyActions({
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
  });

  const items = useMemo<ChapterRewriteItem[]>(() => {
    if (!batch) {
      return orderedChapters
        .filter((chapter) => selectedChapterIds.has(chapter.id))
        .map((chapter) => ({
          id: chapter.id,
          chapter,
          state: "waiting",
          jobId: null,
          preview: "",
          logs: "",
          statusLabel: "等待中",
          errorMessage: null,
          applyErrorMessage: null,
        }));
    }
    return batchItems.map((item) => {
      const chapter = item.chapter ?? chaptersById.get(item.chapter_id);
      const fallbackChapter = chapter ?? buildFallbackChapter(batch, item);
      const display = buildDisplayItem(
        item,
        fallbackChapter,
        previews[item.id] ?? "",
        logsByItemId[item.id] ?? "",
      );
      const applyState = applyStateByItemId[item.id];
      if (applyState === "applying") return { ...display, state: "applying" };
      if (applyState === "failed") return { ...display, state: "apply_failed", applyErrorMessage: "应用改写失败" };
      return display;
    });
  }, [applyStateByItemId, batch, batchItems, chaptersById, logsByItemId, orderedChapters, previews, selectedChapterIds]);

  const activeItem = items.find((item) => item.chapter.id === activeChapterId) ?? items[0] ?? null;
  const hasTaskEntry = Boolean(batch && isBatchActionable(batch));

  return {
    isOpen,
    instruction,
    setInstruction,
    expansionRatioPercent,
    setExpansionRatioPercent,
    orderedChapters,
    selectedChapterIds,
    selectChapter,
    selectCurrentChapter,
    selectAllChapters,
    clearSelectedChapters,
    items,
    activeItem,
    activeChapterId,
    setActiveChapterId,
    activeBatch: batch,
    hasTaskEntry,
    isRunning: isRunning || createMutation.isPending,
    isApplying,
    openRewrite,
    closeRewrite,
    startRewrite,
    applyOne,
    applyAll,
    setIsOpen,
  };
}
