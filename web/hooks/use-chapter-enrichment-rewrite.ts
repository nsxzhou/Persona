import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { ChapterRewriteBatch, ChapterRewriteBatchItem, ProjectChapter } from "@/lib/types";

const POLL_INTERVAL_MS = 1000;

export type ChapterRewriteState =
  | "waiting"
  | "running"
  | "generated"
  | "failed"
  | "applying"
  | "applied"
  | "apply_failed";

export type ChapterRewriteItem = {
  id: string;
  chapter: ProjectChapter;
  state: ChapterRewriteState;
  jobId: string | null;
  preview: string;
  logs: string;
  statusLabel: string;
  errorMessage: string | null;
  applyErrorMessage: string | null;
};

const chapterRewriteBatchKeys = {
  list: (projectId: string) => ["chapter-rewrite-batches", projectId] as const,
  detail: (batchId: string | null) => ["chapter-rewrite-batch", batchId] as const,
};

function sortChapters(chapters: ProjectChapter[]): ProjectChapter[] {
  return [...chapters].sort((left, right) =>
    left.volume_index - right.volume_index || left.chapter_index - right.chapter_index
  );
}

function isBatchActive(batch: Pick<ChapterRewriteBatch, "status">) {
  return batch.status === "pending" || batch.status === "running";
}

function isBatchReviewable(batch: Pick<ChapterRewriteBatch, "status" | "generated_count" | "applied_count">) {
  return batch.status !== "pending" && batch.status !== "running" && batch.generated_count > batch.applied_count;
}

function isBatchActionable(batch: Pick<ChapterRewriteBatch, "status" | "generated_count" | "applied_count">) {
  return isBatchActive(batch) || isBatchReviewable(batch);
}

function mapItemState(item: ChapterRewriteBatchItem): ChapterRewriteState {
  if (item.status === "waiting") return "waiting";
  if (item.status === "running") return "running";
  if (item.status === "generated") return "generated";
  if (item.status === "failed") return "failed";
  return "applied";
}

function buildDisplayItem(
  item: ChapterRewriteBatchItem,
  chapter: ProjectChapter,
  preview: string,
  logs: string,
): ChapterRewriteItem {
  const state = mapItemState(item);
  return {
    id: item.id,
    chapter,
    state,
    jobId: item.child_run_id,
    preview,
    logs,
    statusLabel: item.stage ? `${item.status} / ${item.stage}` : item.status,
    errorMessage: item.error_message,
    applyErrorMessage: null,
  };
}

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
  const [previews, setPreviews] = useState<Record<string, string>>({});
  const [logsByItemId, setLogsByItemId] = useState<Record<string, string>>({});
  const [applyStateByItemId, setApplyStateByItemId] = useState<Record<string, "applying" | "failed">>({});

  const listQuery = useQuery({
    queryKey: chapterRewriteBatchKeys.list(projectId),
    queryFn: () => api.getChapterRewriteBatches({ projectId }),
    refetchInterval: (query) =>
      query.state.data?.some((batch) => isBatchActive(batch)) ? POLL_INTERVAL_MS : false,
  });

  useEffect(() => {
    if (activeBatchId || !listQuery.data?.length) return;
    const candidate = listQuery.data.find(isBatchActionable);
    if (candidate) {
      setActiveBatchId(candidate.id);
    }
  }, [activeBatchId, listQuery.data]);

  const detailQuery = useQuery({
    queryKey: chapterRewriteBatchKeys.detail(activeBatchId),
    queryFn: () => api.getChapterRewriteBatch(activeBatchId!),
    enabled: Boolean(activeBatchId),
    refetchInterval: (query) =>
      query.state.data && isBatchActive(query.state.data) ? POLL_INTERVAL_MS : false,
  });

  const batch = detailQuery.data ?? null;
  const batchItems = useMemo(() => batch?.items ?? [], [batch?.items]);
  const isRunning = Boolean(batch && isBatchActive(batch));
  const isApplying = Object.values(applyStateByItemId).some((state) => state === "applying");

  useEffect(() => {
    if (!batch || isOpen || isBatchActionable(batch)) return;
    setActiveBatchId(null);
    setPreviews({});
    setLogsByItemId({});
    setApplyStateByItemId({});
  }, [batch, isOpen]);

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

  useEffect(() => {
    if (!batch) return;
    for (const item of batchItems) {
      if ((item.status === "generated" || item.status === "applied") && previews[item.id] === undefined) {
        api.getChapterRewriteBatchItemArtifact(batch.id, item.id)
          .then((artifact) => {
            setPreviews((current) => ({ ...current, [item.id]: artifact }));
          })
          .catch(() => {
            setPreviews((current) => ({ ...current, [item.id]: "" }));
          });
      }
    }
  }, [batch, batchItems, previews]);

  const activeItemId = useMemo(() => {
    if (!batch) return null;
    const active = activeChapterId
      ? batchItems.find((item) => item.chapter_id === activeChapterId)
      : null;
    return active?.id ?? batchItems[0]?.id ?? null;
  }, [activeChapterId, batch, batchItems]);

  useEffect(() => {
    if (!batch || !activeItemId) return;
    const item = batchItems.find((candidate) => candidate.id === activeItemId);
    if (!item?.child_run_id) return;
    api.getChapterRewriteBatchItemLogs(batch.id, activeItemId)
      .then((result) => {
        setLogsByItemId((current) => ({ ...current, [activeItemId]: result.content }));
      })
      .catch(() => undefined);
  }, [activeItemId, batch, batchItems]);

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
      setPreviews({});
      setLogsByItemId({});
      setApplyStateByItemId({});
      queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.list(projectId) });
      queryClient.setQueryData(chapterRewriteBatchKeys.detail(created.id), created);
      toast.success("章节改写任务已创建");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "创建章节改写任务失败");
    },
  });

  const openRewrite = useCallback(() => {
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
      setPreviews({});
      setLogsByItemId({});
      setApplyStateByItemId({});
    }
    const defaultChapterId = selectedChapter?.id ?? orderedChapters[0]?.id ?? null;
    setSelectedChapterIds(defaultChapterId ? new Set([defaultChapterId]) : new Set());
    setActiveChapterId(defaultChapterId);
    setExpansionRatioPercent(20);
    setIsOpen(true);
  }, [batch, batchItems, orderedChapters, selectedChapter]);

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

  const applyOne = useCallback(async (chapterId: string) => {
    if (!batch || isBatchActive(batch) || isApplying) return null;
    const item = batchItems.find((candidate) => candidate.chapter_id === chapterId);
    if (!item || item.status !== "generated") return null;
    setApplyStateByItemId((current) => ({ ...current, [item.id]: "applying" }));
    setActiveChapterId(chapterId);
    try {
      const result = await api.applyChapterRewriteBatchItem(batch.id, item.id);
      onApplied(result.chapter);
      queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.detail(batch.id) });
      queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.list(projectId) });
      if (batch.total_count === batch.applied_count + 1) {
        setActiveBatchId(null);
        setPreviews({});
        setLogsByItemId({});
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
  }, [batch, batchItems, isApplying, onApplied, projectId, queryClient]);

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
      await queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.detail(batch.id) });
      await queryClient.invalidateQueries({ queryKey: chapterRewriteBatchKeys.list(projectId) });
      setActiveBatchId(null);
      setPreviews({});
      setLogsByItemId({});
      setApplyStateByItemId({});
      toast.success(`批量应用完成：成功 ${result.applied.length} 章`);
    } catch (error) {
      setApplyStateByItemId({});
      toast.error(error instanceof Error ? error.message : "批量应用失败");
    }
  }, [batch, batchItems, isApplying, onApplied, projectId, queryClient]);

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
      const fallbackChapter: ProjectChapter = chapter ?? {
        id: item.chapter_id,
        project_id: batch.project_id,
        volume_index: 0,
        chapter_index: item.position,
        title: item.chapter_title ?? "未知章节",
        content: "",
        beats_markdown: "",
        summary: "",
        word_count: 0,
        memory_sync_status: null,
        memory_sync_source: null,
        memory_sync_scope: null,
        memory_sync_checked_at: null,
        memory_sync_checked_content_hash: null,
        memory_sync_error_message: null,
        memory_sync_proposed_characters_status: null,
        memory_sync_proposed_state: null,
        memory_sync_proposed_threads: null,
        memory_sync_proposed_summary: null,
        created_at: batch.created_at,
        updated_at: batch.updated_at,
      };
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
