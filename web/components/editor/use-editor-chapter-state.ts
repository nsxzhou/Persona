import { useCallback, useEffect, useMemo } from "react";
import { toast } from "sonner";
import type { StoreApi } from "zustand";
import { useShallow } from "zustand/react/shallow";

import { useSyncChapters } from "@/hooks/use-chapters-query";
import type { ParsedOutline } from "@/lib/outline-parser";
import type { ProjectChapter } from "@/lib/types";

import { useEditorStore } from "./editor-context";
import type { EditorState } from "./editor-store";

export function useEditorChapterState({
  projectId,
  chapters,
  isLoadingChapters,
  parsedOutline,
  store,
  revealLeftPanel,
}: {
  projectId: string;
  chapters: ProjectChapter[];
  isLoadingChapters: boolean;
  parsedOutline: ParsedOutline;
  store: StoreApi<EditorState>;
  revealLeftPanel: () => void;
}) {
  const {
    currentChapter,
    setCurrentChapter,
    selectedVolumeIndex,
    setSelectedVolumeIndex,
    chapterFocusMode,
    setChapterFocusMode,
  } = useEditorStore(useShallow((s: EditorState) => ({
    currentChapter: s.currentChapter,
    setCurrentChapter: s.setCurrentChapter,
    selectedVolumeIndex: s.selectedVolumeIndex,
    setSelectedVolumeIndex: s.setSelectedVolumeIndex,
    chapterFocusMode: s.chapterFocusMode,
    setChapterFocusMode: s.setChapterFocusMode,
  })));

  const selectedChapterRecord = useMemo(() => {
    if (!currentChapter) return null;
    return chapters.find(
      (chapter) =>
        chapter.volume_index === currentChapter.volumeIndex &&
        chapter.chapter_index === currentChapter.chapterIndex,
    ) ?? null;
  }, [chapters, currentChapter]);

  const completedChapters = useMemo(
    () => new Set(chapters.filter((chapter) => chapter.word_count > 0).map((chapter) => chapter.title)),
    [chapters],
  );

  const totalContentLength = useMemo(
    () => chapters.reduce((sum, chapter) => sum + chapter.word_count, 0),
    [chapters],
  );

  const currentChapterContext = useMemo(() => {
    if (!currentChapter || !parsedOutline.volumes.length) return "";
    const volume = parsedOutline.volumes[currentChapter.volumeIndex];
    if (!volume) return "";
    const chapter = volume.chapters[currentChapter.chapterIndex];
    if (!chapter) return "";
    const parts = [`**${chapter.title}**`];
    if (chapter.coreEvent) parts.push(`- 核心事件：${chapter.coreEvent}`);
    if (chapter.emotionArc) parts.push(`- 情绪走向：${chapter.emotionArc}`);
    if (chapter.chapterHook) parts.push(`- 章末钩子：${chapter.chapterHook}`);
    return parts.join("\n");
  }, [currentChapter, parsedOutline]);

  const previousChapterContext = useMemo(() => {
    if (!currentChapter) return "";
    const previousChapters = chapters
      .filter((chapter) => {
        if (chapter.volume_index < currentChapter.volumeIndex) return true;
        if (chapter.volume_index > currentChapter.volumeIndex) return false;
        return chapter.chapter_index < currentChapter.chapterIndex;
      })
      .slice(-3);

    return previousChapters
      .filter((chapter) => chapter.content.trim())
      .map((chapter) => {
        const text = chapter.summary ? chapter.summary : chapter.content.slice(-300);
        return `## ${chapter.title} (摘要)\n\n${text}`;
      })
      .join("\n\n---\n\n");
  }, [chapters, currentChapter]);

  const { mutateAsync: syncChapters } = useSyncChapters();

  useEffect(() => {
    if (!isLoadingChapters && chapters.length === 0) {
      syncChapters(projectId).catch((error: unknown) => {
        toast.error(error instanceof Error ? error.message : "加载章节失败");
      });
    }
  }, [chapters.length, isLoadingChapters, projectId, syncChapters]);

  useEffect(() => {
    if (isLoadingChapters || chapters.length === 0 || currentChapter) return;
    const target = chapters.find((chapter) => chapter.word_count === 0) ?? chapters[0];

    const volume = parsedOutline.volumes[target.volume_index];
    if (!volume || !volume.chapters[target.chapter_index]) {
      return;
    }

    setSelectedVolumeIndex(target.volume_index);
    setCurrentChapter({ volumeIndex: target.volume_index, chapterIndex: target.chapter_index });
    setChapterFocusMode("navigate");
    revealLeftPanel();
  }, [
    chapters,
    currentChapter,
    isLoadingChapters,
    parsedOutline.volumes,
    revealLeftPanel,
    setChapterFocusMode,
    setCurrentChapter,
    setSelectedVolumeIndex,
  ]);

  useEffect(() => {
    if (!selectedChapterRecord) {
      store.getState().setContent("");
      store.getState().setSavedChapterContent("");
      return;
    }
    store.getState().setContent(selectedChapterRecord.content);
    store.getState().setSavedChapterContent(selectedChapterRecord.content);
  }, [selectedChapterRecord?.id, selectedChapterRecord?.content, store]);

  useEffect(() => {
    if (selectedVolumeIndex === null) return;

    const volume = parsedOutline.volumes[selectedVolumeIndex];
    if (!volume) {
      setSelectedVolumeIndex(null);
      setCurrentChapter(null);
      setChapterFocusMode("idle");
      return;
    }

    if (!currentChapter) return;
    const chapter = volume.chapters[currentChapter.chapterIndex];
    if (!chapter) {
      setCurrentChapter(null);
    }
  }, [
    currentChapter,
    parsedOutline,
    selectedVolumeIndex,
    setChapterFocusMode,
    setCurrentChapter,
    setSelectedVolumeIndex,
  ]);

  const selectChapter = useCallback((volumeIndex: number, chapterIndex: number) => {
    setSelectedVolumeIndex(volumeIndex);
    setCurrentChapter({ volumeIndex, chapterIndex });
    setChapterFocusMode("navigate");
  }, [setChapterFocusMode, setCurrentChapter, setSelectedVolumeIndex]);

  const currentVolumeTitle = selectedVolumeIndex !== null
    ? (parsedOutline.volumes[selectedVolumeIndex]?.title.trim() || "未分卷章节")
    : null;
  const currentChapterTitle = currentChapter
    ? parsedOutline.volumes[currentChapter.volumeIndex]?.chapters[currentChapter.chapterIndex]?.title ?? null
    : null;
  const currentVolumeHasChapters = selectedVolumeIndex !== null
    ? (parsedOutline.volumes[selectedVolumeIndex]?.chapters.length ?? 0) > 0
    : true;
  const currentChapterStatus = currentChapter
    ? chapterFocusMode === "generate_beats"
      ? "已定位章节，准备生成节拍"
      : "已定位章节"
    : "请从左侧创作导航选择章节";
  const missingOutlineStatus = selectedVolumeIndex !== null && !currentVolumeHasChapters;

  return {
    currentChapter,
    selectedVolumeIndex,
    chapterFocusMode,
    selectedChapterRecord,
    completedChapters,
    totalContentLength,
    currentChapterContext,
    previousChapterContext,
    currentVolumeTitle,
    currentChapterTitle,
    currentChapterStatus,
    missingOutlineStatus,
    selectChapter,
  };
}
