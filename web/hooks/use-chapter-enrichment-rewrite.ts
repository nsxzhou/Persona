import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { ProjectChapter } from "@/lib/types";

const POLL_INTERVAL_MS = 800;

export type ChapterRewriteState =
  | "waiting"
  | "running"
  | "generated"
  | "failed"
  | "applying"
  | "applied"
  | "apply_failed";

export type ChapterRewriteItem = {
  chapter: ProjectChapter;
  state: ChapterRewriteState;
  jobId: string | null;
  preview: string;
  logs: string;
  statusLabel: string;
  errorMessage: string | null;
  applyErrorMessage: string | null;
};

function buildItem(chapter: ProjectChapter): ChapterRewriteItem {
  return {
    chapter,
    state: "waiting",
    jobId: null,
    preview: "",
    logs: "",
    statusLabel: "等待中",
    errorMessage: null,
    applyErrorMessage: null,
  };
}

function sortChapters(chapters: ProjectChapter[]): ProjectChapter[] {
  return [...chapters].sort((left, right) =>
    left.volume_index - right.volume_index || left.chapter_index - right.chapter_index
  );
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
  const orderedChapters = useMemo(() => sortChapters(chapters), [chapters]);
  const [isOpen, setIsOpen] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [items, setItems] = useState<ChapterRewriteItem[]>([]);
  const [activeChapterId, setActiveChapterId] = useState<string | null>(null);
  const [selectedChapterIds, setSelectedChapterIds] = useState<Set<string>>(new Set());
  const [isRunning, setIsRunning] = useState(false);
  const [isApplying, setIsApplying] = useState(false);

  const resetRunState = useCallback((ids: Set<string>) => {
    setItems(orderedChapters.filter((chapter) => ids.has(chapter.id)).map(buildItem));
    setActiveChapterId((current) => (current && ids.has(current) ? current : [...ids][0] ?? null));
  }, [orderedChapters]);

  const openRewrite = useCallback(() => {
    if (orderedChapters.length === 0) {
      toast.message("请先导入或同步章节");
      return;
    }
    const initialIds = new Set<string>(
      selectedChapter ? [selectedChapter.id] : [orderedChapters[0].id],
    );
    setSelectedChapterIds(initialIds);
    resetRunState(initialIds);
    setIsOpen(true);
  }, [orderedChapters, resetRunState, selectedChapter]);

  const closeRewrite = useCallback(() => {
    if (isRunning || isApplying) return;
    setIsOpen(false);
  }, [isApplying, isRunning]);

  const setItem = useCallback((
    chapterId: string,
    updater: (item: ChapterRewriteItem) => ChapterRewriteItem,
  ) => {
    setItems((current) =>
      current.map((item) => (item.chapter.id === chapterId ? updater(item) : item)),
    );
  }, []);

  const selectChapter = useCallback((chapterId: string, checked: boolean) => {
    if (isRunning || isApplying) return;
    const next = new Set(selectedChapterIds);
    if (checked) next.add(chapterId);
    else next.delete(chapterId);
    setSelectedChapterIds(next);
    resetRunState(next);
  }, [isApplying, isRunning, resetRunState, selectedChapterIds]);

  const readLogs = useCallback(async (jobId: string, chapterId: string, offset: number) => {
    const result = await api.getNovelChapterRewriteJobLogs(jobId, offset);
    setItem(chapterId, (item) => ({
      ...item,
      logs: result.truncated ? result.content : item.logs + result.content,
    }));
    return result.next_offset;
  }, [setItem]);

  const runOne = useCallback(async (chapter: ProjectChapter, trimmedInstruction: string) => {
    setActiveChapterId(chapter.id);
    setItem(chapter.id, (item) => ({
      ...item,
      state: "running",
      statusLabel: "提交中",
      logs: "",
      preview: "",
      errorMessage: null,
      applyErrorMessage: null,
    }));
    const job = await api.createNovelChapterRewriteJob({
      project_id: projectId,
      chapter_id: chapter.id,
      instruction: trimmedInstruction,
    });
    setItem(chapter.id, (item) => ({ ...item, jobId: job.id }));

    let nextOffset = 0;
    let firstPoll = true;
    while (true) {
      if (firstPoll) {
        firstPoll = false;
      } else {
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
      const status = await api.getNovelChapterRewriteJobStatus(job.id);
      setItem(chapter.id, (item) => ({
        ...item,
        statusLabel: status.stage ? `${status.status} / ${status.stage}` : status.status,
      }));
      nextOffset = await readLogs(job.id, chapter.id, nextOffset);
      if (status.status === "succeeded") {
        const artifact = await api.getNovelChapterRewriteJobArtifact(job.id);
        setItem(chapter.id, (item) => ({
          ...item,
          state: "generated",
          preview: artifact,
          statusLabel: "generated",
        }));
        return;
      }
      if (status.status === "failed") {
        throw new Error(status.error_message || "章节改写失败");
      }
      if (status.status === "paused") {
        throw new Error("章节改写已暂停");
      }
    }
  }, [projectId, readLogs, setItem]);

  const startRewrite = useCallback(async () => {
    if (isRunning) return;
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
    resetRunState(selectedChapterIds);
    setIsRunning(true);
    let generatedCount = 0;
    for (const chapter of selected) {
      try {
        await runOne(chapter, trimmed);
        generatedCount += 1;
      } catch (error) {
        const message = error instanceof Error ? error.message : "章节改写失败";
        setItem(chapter.id, (item) => ({
          ...item,
          state: "failed",
          statusLabel: "failed",
          errorMessage: message,
        }));
      }
    }
    setIsRunning(false);
    toast[generatedCount > 0 ? "success" : "error"](
      generatedCount > 0
        ? `已生成 ${generatedCount}/${selected.length} 个章节预览`
        : "章节改写失败",
    );
  }, [instruction, isRunning, orderedChapters, resetRunState, runOne, selectedChapterIds, setItem]);

  const applyOne = useCallback(async (chapterId: string) => {
    const item = items.find((candidate) => candidate.chapter.id === chapterId);
    if (!item?.jobId || !item.preview.trim() || isApplying) return null;
    setIsApplying(true);
    setActiveChapterId(chapterId);
    setItem(chapterId, (current) => ({
      ...current,
      state: "applying",
      applyErrorMessage: null,
    }));
    try {
      const result = await api.applyNovelChapterRewriteJob(item.jobId);
      onApplied(result.chapter);
      setItem(chapterId, (current) => ({ ...current, state: "applied" }));
      toast.success("章节正文已替换");
      return result.chapter;
    } catch (error) {
      const message = error instanceof Error ? error.message : "应用改写失败";
      setItem(chapterId, (current) => ({
        ...current,
        state: "apply_failed",
        applyErrorMessage: message,
      }));
      toast.error(message);
      return null;
    } finally {
      setIsApplying(false);
    }
  }, [isApplying, items, onApplied, setItem]);

  const applyAll = useCallback(async () => {
    if (isApplying) return;
    const generated = items.filter((item) => item.jobId && item.preview.trim() && item.state !== "applied");
    if (generated.length === 0) {
      toast.message("没有可应用的改写预览");
      return;
    }
    setIsApplying(true);
    let successCount = 0;
    let failureCount = 0;
    for (const item of generated) {
      setActiveChapterId(item.chapter.id);
      setItem(item.chapter.id, (current) => ({
        ...current,
        state: "applying",
        applyErrorMessage: null,
      }));
      try {
        const result = await api.applyNovelChapterRewriteJob(item.jobId!);
        onApplied(result.chapter);
        successCount += 1;
        setItem(item.chapter.id, (current) => ({ ...current, state: "applied" }));
      } catch (error) {
        failureCount += 1;
        const message = error instanceof Error ? error.message : "应用改写失败";
        setItem(item.chapter.id, (current) => ({
          ...current,
          state: "apply_failed",
          applyErrorMessage: message,
        }));
      }
    }
    setIsApplying(false);
    toast[successCount > 0 ? "success" : "error"](
      `批量应用完成：成功 ${successCount} 章，失败 ${failureCount} 章`,
    );
  }, [isApplying, items, onApplied, setItem]);

  const activeItem = items.find((item) => item.chapter.id === activeChapterId) ?? items[0] ?? null;

  return {
    isOpen,
    instruction,
    setInstruction,
    orderedChapters,
    selectedChapterIds,
    selectChapter,
    items,
    activeItem,
    activeChapterId,
    setActiveChapterId,
    isRunning,
    isApplying,
    openRewrite,
    closeRewrite,
    startRewrite,
    applyOne,
    applyAll,
    setIsOpen,
  };
}
