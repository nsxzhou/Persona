import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import React from "react";
import { useEditorContext, useEditorStore } from "./editor-context";
import type { EditorState } from "./editor-store";
import { useShallow } from "zustand/react/shallow";
import { useEditorAutosave } from "@/hooks/use-editor-autosave";
import { useEditorCompletion } from "@/hooks/use-editor-completion";
import { useBeatGeneration } from "@/hooks/use-beat-generation";
import { useChapterMemorySync } from "@/hooks/use-chapter-memory-sync";
import { parseOutline } from "@/lib/outline-parser";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useProjectQuery, useProjectBibleQuery, useUpdateProject, useUpdateProjectBible } from "@/hooks/use-project-query";
import { EditorLayout } from "./editor-layout";
import { BibleDiffDialog } from "@/components/bible-diff-dialog";
import { MemorySyncButton } from "@/components/memory-sync-button";
import { BeatPanel } from "@/components/beat-panel";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import type { ProjectChapter, ProjectBible } from "@/lib/types";

const EditorTextarea = React.memo(({ 
  disabled, 
  placeholder, 
  className, 
  handleKeyDown 
}: { 
  disabled: boolean; 
  placeholder: string; 
  className: string; 
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void; 
}) => {
  const content = useEditorStore(s => s.content);
  const setContent = useEditorStore(s => s.setContent);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  return (
    <textarea
      ref={textareaRef}
      value={content}
      onChange={(e) => setContent(e.target.value)}
      onKeyDown={handleKeyDown}
      disabled={disabled}
      placeholder={placeholder}
      className={className}
      style={{ fontFamily: "var(--font-serif), serif" }}
    />
  );
});
EditorTextarea.displayName = "EditorTextarea";

const DEFAULT_BIBLE = { runtime_state: "", runtime_threads: "", outline_detail: "" };

export function EditorContentArea({ 
  activeProfileName, 
  initialProjectBible 
}: { 
  activeProfileName?: string;
  initialProjectBible?: ProjectBible;
}) {
  const router = useRouter();
  const { project: initialProject, store } = useEditorContext();
  const {
    chapters,
    setChapters,
    isLoadingChapters,
    setIsLoadingChapters,
    currentChapter,
    setCurrentChapter,
    selectedVolumeIndex,
    setSelectedVolumeIndex,
    chapterFocusMode,
    setChapterFocusMode,
    isLeftExpanded,
    setIsLeftExpanded,
    isRightExpanded,
    setIsRightExpanded,
    leftPanelMode,
    setLeftPanelMode,
  } = useEditorStore(useShallow((s: EditorState) => ({
    chapters: s.chapters,
    setChapters: s.setChapters,
    isLoadingChapters: s.isLoadingChapters,
    setIsLoadingChapters: s.setIsLoadingChapters,
    currentChapter: s.currentChapter,
    setCurrentChapter: s.setCurrentChapter,
    selectedVolumeIndex: s.selectedVolumeIndex,
    setSelectedVolumeIndex: s.setSelectedVolumeIndex,
    chapterFocusMode: s.chapterFocusMode,
    setChapterFocusMode: s.setChapterFocusMode,
    isLeftExpanded: s.isLeftExpanded,
    setIsLeftExpanded: s.setIsLeftExpanded,
    isRightExpanded: s.isRightExpanded,
    setIsRightExpanded: s.setIsRightExpanded,
    leftPanelMode: s.leftPanelMode,
    setLeftPanelMode: s.setLeftPanelMode,
  })));

  const hasChapterContent = useEditorStore(s => s.content.trim().length > 0);

  const { data: project = initialProject } = useProjectQuery(initialProject.id, initialProject);
  const { data: projectBible } = useProjectBibleQuery(initialProject.id, initialProjectBible);
  
  const updateProjectMutation = useUpdateProject();
  const updateProjectBibleMutation = useUpdateProjectBible();

  const parsedOutline = useMemo(
    () => parseOutline(projectBible?.outline_detail ?? ""),
    [projectBible?.outline_detail],
  );

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
    () =>
      chapters.reduce(
        (sum, chapter) => sum + chapter.word_count,
        0,
      ),
    [chapters],
  );

  const currentChapterContext = useMemo(() => {
    if (!currentChapter || !parsedOutline.volumes.length) return "";
    const vol = parsedOutline.volumes[currentChapter.volumeIndex];
    if (!vol) return "";
    const ch = vol.chapters[currentChapter.chapterIndex];
    if (!ch) return "";
    const parts = [`**${ch.title}**`];
    if (ch.coreEvent) parts.push(`- 核心事件：${ch.coreEvent}`);
    if (ch.emotionArc) parts.push(`- 情绪走向：${ch.emotionArc}`);
    if (ch.chapterHook) parts.push(`- 章末钩子：${ch.chapterHook}`);
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
      .slice(-3); // 仅取最近 3 章

    return previousChapters
      .filter((chapter) => chapter.content.trim())
      .map((chapter) => {
        const text = chapter.summary ? chapter.summary : chapter.content.slice(-300);
        return `## ${chapter.title} (摘要)\n\n${text}`;
      })
      .join("\n\n---\n\n");
  }, [chapters, currentChapter]);

  const syncPersistedChapter = useCallback(
    (updatedChapter: ProjectChapter) => {
      setChapters((prev) =>
        prev.map((chapter) =>
          chapter.id === updatedChapter.id ? { ...chapter, ...updatedChapter } : chapter,
        ),
      );
      if (selectedChapterRecord?.id === updatedChapter.id) {
        store.getState().setSavedChapterContent(updatedChapter.content);
      }
      return updatedChapter;
    },
    [selectedChapterRecord?.id, setChapters],
  );

  const persistChapterUpdate = useCallback(
    async (chapterId: string, payload: Parameters<typeof api.updateProjectChapter>[2]) => {
      const updated = await api.updateProjectChapter(project.id, chapterId, payload);
      return syncPersistedChapter(updated);
    },
    [project.id, syncPersistedChapter],
  );

  const persistProjectUpdate = useCallback(
    async (payload: Parameters<typeof api.updateProject>[1], options: { successMessage?: string; errorMessage?: string } = {}) => {
      try {
        await updateProjectMutation.mutateAsync({ id: project.id, payload });
        if (options.successMessage) toast.success(options.successMessage);
      } catch {
        if (options.errorMessage) toast.error(options.errorMessage);
      }
    },
    [project.id, updateProjectMutation]
  );

  const persistProjectBibleUpdate = useCallback(
    async (payload: Parameters<typeof api.updateProjectBible>[1], options: { successMessage?: string; errorMessage?: string } = {}) => {
      try {
        await updateProjectBibleMutation.mutateAsync({ id: project.id, payload });
        if (options.successMessage) toast.success(options.successMessage);
      } catch {
        if (options.errorMessage) toast.error(options.errorMessage);
      }
    },
    [project.id, updateProjectBibleMutation]
  );

  const persistProjectField = useCallback(
    async (field: string, value: string) => {
      if (field === "description") {
        await persistProjectUpdate({ [field]: value }, { errorMessage: "保存失败" });
      } else {
        await persistProjectBibleUpdate({ [field]: value }, { errorMessage: "保存失败" });
      }
    },
    [persistProjectUpdate, persistProjectBibleUpdate],
  );

  const {
    bibleDiff,
    isChecking: isCheckingMemorySync,
    chapterSyncSnapshot,
    handleGeneratedContent,
    handleManualSync,
    handleAutoChapterSync,
    markSyncFailed,
    openStoredDiff,
    acceptRuntimeUpdate,
    dismissRuntimeUpdate,
  } = useChapterMemorySync({
    projectId: project.id,
    projectBible: (projectBible ?? { characters_status: "", runtime_state: "", runtime_threads: "" }) as any,
    selectedChapter: selectedChapterRecord,
    getCurrentContent: () => store.getState().content,
    persistProjectBibleUpdate,
    persistChapterUpdate,
  });

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleBeatExpandCompleted = useCallback(
    async (beatsProse: string) => {
      if (project.auto_sync_memory) {
        await handleAutoChapterSync(beatsProse);
      }
    },
    [handleAutoChapterSync, project.auto_sync_memory],
  );

  const handleToggleAutoSyncMemory = useCallback(
    async (nextValue: boolean) => {
      await persistProjectUpdate(
        { auto_sync_memory: nextValue },
        { errorMessage: "保存自动同步设置失败" },
      );
    },
    [persistProjectUpdate],
  );

  const { isGenerating: isStreamingCompletion, handleGenerate: handleContinueWrite, handleStop: handleStopWrite } = useEditorCompletion({
    project: project,
    textareaRef,
    onGeneratedContent: handleGeneratedContent,
    currentChapterContext,
    previousChapterContext,
    totalContentLength,
    disabled: !selectedChapterRecord,
  });

  const {
    beats: beatList,
    setBeats: setBeatList,
    currentBeatIndex: activeBeatIndex,
    isGeneratingBeats: isGeneratingBeatPlan,
    isExpandingBeat: isExpandingBeatProse,
    handleGenerateBeats: handleGenerateBeatPlan,
    handleStartBeatExpand: handleExpandBeats,
  } = useBeatGeneration({
    project: project,
    projectBible: (projectBible ?? DEFAULT_BIBLE) as any,
    textareaRef,
    isGenerating: isStreamingCompletion,
    currentChapterContext,
    previousChapterContext,
    totalContentLength,
    disabled: !selectedChapterRecord,
    onBeatExpandCompleted: handleBeatExpandCompleted,
  });

  const { isSaving, saveNow, flushPendingSave, clearSaveError } = useEditorAutosave(
    project.id,
    selectedChapterRecord?.id ?? null,
    isStreamingCompletion || isExpandingBeatProse,
    syncPersistedChapter,
  );

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
  }, [markSyncFailed, saveNow]);

  const handleManualMemorySync = useCallback(async () => {
    if (!selectedChapterRecord) return;
    const content = store.getState().content;
    const savedChapterContent = store.getState().savedChapterContent;

    const hasUnsavedChanges = content !== savedChapterContent;
    if (
      !hasUnsavedChanges &&
      selectedChapterRecord.memory_sync_status === "pending_review" &&
      (selectedChapterRecord.memory_sync_proposed_state !== null ||
        selectedChapterRecord.memory_sync_proposed_threads !== null)
    ) {
      openStoredDiff();
      return;
    }

    if (
      !hasUnsavedChanges &&
      (selectedChapterRecord.memory_sync_status === "synced" ||
        selectedChapterRecord.memory_sync_status === "no_change")
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
    selectedChapterRecord,
  ]);

  const handleForceMemorySync = useCallback(async () => {
    if (!selectedChapterRecord) return;
    const checkedContent = await saveCurrentChapterForSync();
    if (checkedContent === null) return;
    await handleManualSync(checkedContent);
  }, [handleManualSync, saveCurrentChapterForSync, selectedChapterRecord]);

  const handleRetryMemoryProposal = useCallback(
    async (feedback: string) => {
      if (!selectedChapterRecord) return;
      const checkedContent = await saveCurrentChapterForSync();
      if (checkedContent === null) return;
      const previousOutput = selectedChapterRecord.memory_sync_proposed_state
        || selectedChapterRecord.memory_sync_proposed_threads
        ? JSON.stringify({
            runtime_state: selectedChapterRecord.memory_sync_proposed_state ?? "",
            runtime_threads: selectedChapterRecord.memory_sync_proposed_threads ?? "",
          })
        : undefined;
      await handleManualSync(checkedContent, {
        previousOutput,
        userFeedback: feedback || undefined,
      });
    },
    [handleManualSync, saveCurrentChapterForSync, selectedChapterRecord],
  );

  useEffect(() => {
    let cancelled = false;
    async function loadChapters() {
      setIsLoadingChapters(true);
      try {
        const loaded = await api.getProjectChapters(project.id);
        const next = loaded.length > 0 ? loaded : await api.syncProjectChapters(project.id);
        if (!cancelled) setChapters(next);
      } catch (e: unknown) {
        if (!cancelled) toast.error(e instanceof Error ? e.message : "加载章节失败");
      } finally {
        if (!cancelled) setIsLoadingChapters(false);
      }
    }
    loadChapters();
    return () => {
      cancelled = true;
    };
  }, [project.id, setChapters, setIsLoadingChapters]);

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
    setIsLeftExpanded(true);
  }, [chapters, currentChapter, isLoadingChapters, parsedOutline.volumes, setChapterFocusMode, setCurrentChapter, setIsLeftExpanded, setSelectedVolumeIndex]);

  useEffect(() => {
    if (!selectedChapterRecord) {
      store.getState().setContent("");
      store.getState().setSavedChapterContent("");
      return;
    }
    store.getState().setContent(selectedChapterRecord.content);
    store.getState().setSavedChapterContent(selectedChapterRecord.content);
  }, [selectedChapterRecord?.id, selectedChapterRecord?.content]);

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
  }, [currentChapter, parsedOutline, selectedVolumeIndex, setChapterFocusMode, setCurrentChapter, setSelectedVolumeIndex]);

  const toggleLeft = useCallback(() => {
    setLeftPanelMode("navigation");
    setIsLeftExpanded(true);
    if (window.innerWidth < 1024) setIsRightExpanded(false);
  }, [setIsLeftExpanded, setIsRightExpanded, setLeftPanelMode]);

  const openSettings = useCallback(() => {
    setLeftPanelMode("settings");
    setIsLeftExpanded(true);
    if (window.innerWidth < 1024) setIsRightExpanded(false);
  }, [setIsLeftExpanded, setIsRightExpanded, setLeftPanelMode]);

  const toggleRight = useCallback(() => {
    if (!selectedChapterRecord) return;
    setIsRightExpanded((prev) => {
      const next = !prev;
      if (next && window.innerWidth < 1024) setIsLeftExpanded(false);
      return next;
    });
  }, [selectedChapterRecord, setIsLeftExpanded, setIsRightExpanded]);

  const handleGenerateBeatsForChapter = useCallback(() => {
    if (!selectedChapterRecord) return;
    setIsRightExpanded(true);
    setTimeout(() => handleGenerateBeatPlan(), 100);
  }, [handleGenerateBeatPlan, selectedChapterRecord, setIsRightExpanded]);

  const handleSelectChapter = useCallback(async (volumeIndex: number, chapterIndex: number) => {
    try {
      await flushPendingSave();
      clearSaveError();
    } catch (e) {
      console.error("Failed to flush pending save before chapter switch:", e);
      toast.error("当前章节保存失败，无法切换，请检查网络");
      return;
    }
    setSelectedVolumeIndex(volumeIndex);
    setCurrentChapter({ volumeIndex, chapterIndex });
    setChapterFocusMode("navigate");
    setIsLeftExpanded(true);
    setLeftPanelMode("navigation");
    setBeatList([]);
  }, [clearSaveError, flushPendingSave, setBeatList, setChapterFocusMode, setCurrentChapter, setIsLeftExpanded, setLeftPanelMode, setSelectedVolumeIndex]);

  const handleGoGenerateVolume = useCallback(
    (volumeIndex: number) => {
      router.push(`/projects/${project.id}?tab=outline_detail&volumeIndex=${volumeIndex}`);
    },
    [project.id, router],
  );

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

  const chapterBannerAction = missingOutlineStatus && selectedVolumeIndex !== null ? (
    <Button variant="outline" size="sm" onClick={() => handleGoGenerateVolume(selectedVolumeIndex)}>
      去生成本卷章节细纲
    </Button>
  ) : currentChapter && selectedChapterRecord ? (
    <Button className="gap-2" size="sm" onClick={handleGenerateBeatsForChapter}>
      <Sparkles className="h-4 w-4" />
      为当前章节生成节拍
    </Button>
  ) : (
    <Button variant="outline" size="sm" onClick={toggleLeft}>
      打开创作导航
    </Button>
  );

  const editorMaxWidth = isLeftExpanded && isRightExpanded
    ? "max-w-[600px]"
    : isLeftExpanded || isRightExpanded
      ? "max-w-[680px]"
      : "max-w-[720px]";

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape" && isStreamingCompletion) {
      e.preventDefault();
      handleStopWrite();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "b") {
      e.preventDefault();
      toggleLeft();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "j") {
      e.preventDefault();
      toggleRight();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "j") {
      e.preventDefault();
      handleContinueWrite();
    }
  }, [handleContinueWrite, handleStopWrite, isStreamingCompletion, toggleLeft, toggleRight]);

  return (
    <>
      <EditorLayout
        projectId={project.id}
        projectName={project.name}
        activeProfileName={activeProfileName}
        isSaving={isSaving}
        isStreamingCompletion={isStreamingCompletion}
        isExpandingBeatProse={isExpandingBeatProse}
        isLeftExpanded={isLeftExpanded}
        isRightExpanded={isRightExpanded}
        leftPanelMode={leftPanelMode}
        toggleLeft={toggleLeft}
        openSettings={openSettings}
        toggleRight={toggleRight}
        handleStopWrite={handleStopWrite}
        handleContinueWrite={handleContinueWrite}
        missingOutlineStatus={missingOutlineStatus}
        currentVolumeTitle={currentVolumeTitle}
        currentChapterTitle={currentChapterTitle}
        currentChapterStatus={currentChapterStatus}
        chapterBannerAction={chapterBannerAction}
        canContinueWrite={Boolean(project.style_profile_id && selectedChapterRecord)}
        memorySyncButton={
          <MemorySyncButton
            snapshot={
              chapterSyncSnapshot
                ? {
                    status: chapterSyncSnapshot.status ?? null,
                    source: chapterSyncSnapshot.source ?? null,
                    checkedAt: chapterSyncSnapshot.checkedAt ?? null,
                    errorMessage: chapterSyncSnapshot.errorMessage ?? null,
                  }
                : null
            }
            isChecking={isCheckingMemorySync}
            disabled={!selectedChapterRecord}
            onClick={handleManualMemorySync}
            onForceRerun={handleForceMemorySync}
          />
        }
        sidePanelProps={{
          project: project,
          projectBible: projectBible ?? { characters_status: "", runtime_state: "", runtime_threads: "", outline_detail: "" } as any,
          contentLength: totalContentLength,
          parsedOutline: parsedOutline,
          currentChapter: currentChapter,
          completedChapters: completedChapters,
          onSelectChapter: handleSelectChapter,
          onGenerateBeatsForChapter: handleGenerateBeatsForChapter,
          onCollapse: () => setIsLeftExpanded(false),
          onFieldChange: undefined,
          onPersistField: persistProjectField,
          onToggleAutoSyncMemory: handleToggleAutoSyncMemory,
          onGoGenerateVolume: handleGoGenerateVolume,
          mode: leftPanelMode,
        }}
        rightPanel={
          <BeatPanel
            beats={beatList}
            currentBeatIndex={activeBeatIndex}
            isExpandingBeat={isExpandingBeatProse}
            isGeneratingBeats={isGeneratingBeatPlan}
            onGenerateBeats={handleGenerateBeatPlan}
            onRegenerateBeats={(feedback) =>
              handleGenerateBeatPlan({
                previousOutput: beatList.length > 0 ? JSON.stringify(beatList) : undefined,
                userFeedback: feedback || undefined,
              })
            }
            onRegenerateExpansion={(feedback) =>
              handleExpandBeats({
                previousOutput: store.getState().content || undefined,
                userFeedback: feedback || undefined,
              })
            }
            onBeatsChange={setBeatList}
            onStartExpand={handleExpandBeats}
            onClose={() => setIsRightExpanded(false)}
            disabled={!selectedChapterRecord}
            hasChapterContent={hasChapterContent}
          />
        }
        hasBeats={beatList.length > 0}
        activeBeatIndex={activeBeatIndex}
        totalBeats={beatList.length}
        canOpenRightPanel={Boolean(selectedChapterRecord)}
      >
        <EditorTextarea
          handleKeyDown={handleKeyDown}
          disabled={!selectedChapterRecord || isStreamingCompletion || isExpandingBeatProse}
          placeholder={selectedChapterRecord ? "开始创作... (按 ⌘J 进行 AI 续写)" : "请先选择章节..."}
          className={`w-full ${editorMaxWidth} h-full p-8 md:p-12 resize-none bg-transparent outline-none text-lg leading-relaxed shadow-none border-none focus:ring-0 text-foreground/90 placeholder:text-muted-foreground/50 disabled:cursor-not-allowed`}
        />
      </EditorLayout>

      <BibleDiffDialog
          open={bibleDiff.open}
          currentCharactersStatus={bibleDiff.currentCharactersStatus}
          proposedCharactersStatus={bibleDiff.proposedCharactersStatus}
          currentState={bibleDiff.currentState}
          proposedState={bibleDiff.proposedState}
          currentThreads={bibleDiff.currentThreads}
          proposedThreads={bibleDiff.proposedThreads}
          proposedSummary={bibleDiff.proposedSummary}
          chapterTitle={selectedChapterRecord?.title ?? currentChapterTitle ?? null}
          source={chapterSyncSnapshot?.source ?? null}
          onAccept={acceptRuntimeUpdate}
          onRetry={handleRetryMemoryProposal}
          onDismiss={dismissRuntimeUpdate}
        />
    </>
  );
}

function getVolumeTitle(title: string) {
  return title.trim() || "未分卷章节";
}
