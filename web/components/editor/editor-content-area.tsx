import { useCallback, useEffect, useMemo, useRef, type KeyboardEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useShallow } from "zustand/react/shallow";
import { Loader2, Sparkles } from "lucide-react";

import { BeatPanel } from "@/components/beat-panel";
import { EditorSidePanel } from "@/components/editor-side-panel";
import { EditorLayout } from "./editor-layout";
import { EditorHeaderActions, EditorQuickActions } from "./editor-header-actions";
import { useEditorAutosave } from "@/hooks/use-editor-autosave";
import { useBeatGeneration } from "@/hooks/use-beat-generation";
import { useChapterEnrichmentRewrite } from "@/hooks/use-chapter-enrichment-rewrite";
import { useChapterMemorySync } from "@/hooks/use-chapter-memory-sync";
import { useChaptersQuery } from "@/hooks/use-chapters-query";
import { useProjectBibleQuery, useProjectQuery } from "@/hooks/use-project-query";
import { useSelectionRewrite } from "@/hooks/use-selection-rewrite";
import { parseOutline } from "@/lib/outline-parser";
import type { ProjectBible } from "@/lib/types";

import { DEFAULT_BIBLE } from "./editor-defaults";
import { useEditorContext, useEditorStore } from "./editor-context";
import type { EditorState } from "./editor-store";
import { useEditorPersistence } from "./editor-persistence";
import { getEditorContentMaxWidth } from "./editor-content-area/editor-content-utils";
import { EditorContentBanner } from "./editor-content-area/editor-content-banner";
import { EditorContentDialogs } from "./editor-content-area/editor-content-dialogs";
import { EditorContentRightPanelToggle } from "./editor-content-area/editor-content-right-panel-toggle";
import { EditorContentTextarea } from "./editor-content-area/editor-content-textarea";
import { useEditorChapterState } from "./use-editor-chapter-state";
import { useEditorMemoryActions } from "./use-editor-memory-actions";

export function EditorContentArea({ 
  activeProfileName, 
  initialProjectBible 
}: { 
  activeProfileName?: string;
  initialProjectBible?: ProjectBible;
}) {
  const router = useRouter();
  const { project: initialProject, store } = useEditorContext();
  const queryClient = useQueryClient();
  const { data: chapters = [], isLoading: isLoadingChapters } = useChaptersQuery(initialProject.id);

  const {
    isLeftExpanded,
    setIsLeftExpanded,
    isRightExpanded,
    setIsRightExpanded,
    leftPanelMode,
    setLeftPanelMode,
  } = useEditorStore(useShallow((s: EditorState) => ({
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
  const isImportedRewriteProject = project.project_origin === "txt_import_rewrite";
  
  const parsedOutline = useMemo(
    () => parseOutline(projectBible?.outline_detail ?? ""),
    [projectBible?.outline_detail],
  );

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const revealLeftPanel = useCallback(() => {
    setIsLeftExpanded(true);
  }, [setIsLeftExpanded]);

  const {
    currentChapter,
    selectedVolumeIndex,
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
  } = useEditorChapterState({
    projectId: project.id,
    chapters,
    isLoadingChapters,
    parsedOutline,
    store,
    revealLeftPanel,
  });

  const {
    syncPersistedChapter,
    persistChapterUpdate,
    persistProjectUpdate,
    persistProjectBibleUpdate,
    persistProjectField,
  } = useEditorPersistence({
    projectId: project.id,
    queryClient,
    selectedChapterId: selectedChapterRecord?.id ?? null,
    store,
  });

  const {
    bibleDiff,
    isChecking: isCheckingMemorySync,
    chapterSyncSnapshot,
    handleManualSync,
    handleAutoChapterSync,
    markSyncFailed,
    openStoredDiff,
    acceptRuntimeUpdate,
    dismissRuntimeUpdate,
  } = useChapterMemorySync({
    projectId: project.id,
    projectBible: projectBible ?? DEFAULT_BIBLE,
    selectedChapter: selectedChapterRecord,
    getCurrentContent: () => store.getState().content,
    persistProjectBibleUpdate,
    persistChapterUpdate,
  });

  const handleToggleAutoSyncMemory = useCallback(
    async (nextValue: boolean) => {
      await persistProjectUpdate(
        { auto_sync_memory: nextValue },
        { errorMessage: "保存自动同步设置失败" },
      );
    },
    [persistProjectUpdate],
  );

  const {
    isOpen: isRewriteOpen,
    isGenerating: isRewritingSelection,
    selection: rewriteSelection,
    instruction: rewriteInstruction,
    setInstruction: setRewriteInstruction,
    preview: rewritePreview,
    openRewrite: handleOpenRewrite,
    closeRewrite: handleCloseRewrite,
    generatePreview: handleGenerateRewritePreview,
    applyPreview: handleApplyRewritePreview,
  } = useSelectionRewrite({
    project: project,
    textareaRef,
    currentChapterContext,
    previousChapterContext,
    totalContentLength,
    chapterId: selectedChapterRecord?.id ?? null,
    disabled: !selectedChapterRecord,
  });

  const {
    isOpen: isChapterRewriteOpen,
    instruction: chapterRewriteInstruction,
    setInstruction: setChapterRewriteInstruction,
    expansionRatioPercent: chapterRewriteExpansionRatioPercent,
    setExpansionRatioPercent: setChapterRewriteExpansionRatioPercent,
    orderedChapters: chapterRewriteChapters,
    selectedChapterIds,
    selectChapter: selectChapterForRewrite,
    selectCurrentChapter: selectCurrentChapterForRewrite,
    selectAllChapters: selectAllChaptersForRewrite,
    clearSelectedChapters: clearSelectedChaptersForRewrite,
    items: chapterRewriteItems,
    activeItem: activeChapterRewriteItem,
    activeChapterId: activeChapterRewriteId,
    setActiveChapterId: setActiveChapterRewriteId,
    isRunning: isChapterRewriteRunning,
    isApplying: isChapterRewriteApplying,
    activeBatch: activeChapterRewriteBatch,
    hasTaskEntry: hasChapterRewriteTaskEntry,
    openRewrite: handleOpenChapterRewrite,
    closeRewrite: handleCloseChapterRewrite,
    startRewrite: handleStartChapterRewrite,
    applyOne: handleApplyChapterRewrite,
    applyAll: handleApplyAllChapterRewrites,
  } = useChapterEnrichmentRewrite({
    projectId: project.id,
    chapters,
    selectedChapter: selectedChapterRecord,
    onApplied: (updatedChapter) => {
      syncPersistedChapter(updatedChapter);
      if (selectedChapterRecord?.id === updatedChapter.id) {
        store.getState().setContent(updatedChapter.content);
        store.getState().setSavedChapterContent(updatedChapter.content);
      }
    },
  });

  const handleOpenSelectedChapterRewrite = useCallback(() => {
    handleOpenChapterRewrite({
      selectCurrentChapter: true,
      preserveInstruction: true,
    });
  }, [handleOpenChapterRewrite]);

  const beatExpandCompletedRef = useRef<(beatsProse: string) => Promise<void> | void>(() => {});

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
    projectBible: projectBible ?? DEFAULT_BIBLE,
    textareaRef,
    isGenerating: isRewritingSelection,
    currentChapterContext,
    previousChapterContext,
    totalContentLength,
    chapterId: selectedChapterRecord?.id ?? null,
    disabled: !selectedChapterRecord,
    onBeatExpandCompleted: (beatsProse) => beatExpandCompletedRef.current(beatsProse),
  });

  const { isSaving, saveNow, flushPendingSave, clearSaveError } = useEditorAutosave(
    project.id,
    selectedChapterRecord?.id ?? null,
    isRewritingSelection || isExpandingBeatProse || isChapterRewriteRunning || isChapterRewriteApplying,
    syncPersistedChapter,
  );

  useEffect(() => {
    beatExpandCompletedRef.current = async (beatsProse: string) => {
      try {
        store.getState().setContent(beatsProse);
        const savedChapter = await saveNow(beatsProse);
        if (project.auto_sync_memory) {
          await handleAutoChapterSync(savedChapter.content);
        }
      } catch {
        // saveNow already surfaced the error; do not continue to memory sync.
      }
    };
  }, [handleAutoChapterSync, project.auto_sync_memory, saveNow, store]);

  const {
    memorySyncButtonSnapshot,
    handleManualMemorySync,
    handleForceMemorySync,
    handleRetryMemoryProposal,
  } = useEditorMemoryActions({
    store,
    selectedChapter: selectedChapterRecord,
    chapterSyncSnapshot,
    saveNow,
    handleManualSync,
    markSyncFailed,
    openStoredDiff,
  });

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
    if (isImportedRewriteProject) return;
    if (!selectedChapterRecord) return;
    setIsRightExpanded((prev) => {
      const next = !prev;
      if (next && window.innerWidth < 1024) setIsLeftExpanded(false);
      return next;
    });
  }, [isImportedRewriteProject, selectedChapterRecord, setIsLeftExpanded, setIsRightExpanded]);

  const handleGenerateBeatsForChapter = useCallback(() => {
    if (isImportedRewriteProject) return;
    if (!selectedChapterRecord) return;
    setIsRightExpanded(true);
    setTimeout(() => handleGenerateBeatPlan(), 100);
  }, [handleGenerateBeatPlan, isImportedRewriteProject, selectedChapterRecord, setIsRightExpanded]);

  const handleSelectChapter = useCallback(async (volumeIndex: number, chapterIndex: number) => {
    try {
      await flushPendingSave();
      clearSaveError();
    } catch (e) {
      console.error("Failed to flush pending save before chapter switch:", e);
      toast.error("当前章节保存失败，无法切换，请检查网络");
      return;
    }
    selectChapter(volumeIndex, chapterIndex);
    setIsLeftExpanded(true);
    setLeftPanelMode("navigation");
    setBeatList([]);
  }, [clearSaveError, flushPendingSave, selectChapter, setBeatList, setIsLeftExpanded, setLeftPanelMode]);

  const handleGoGenerateVolume = useCallback(
    (volumeIndex: number) => {
      if (isImportedRewriteProject) return;
      router.push(`/projects/${project.id}?tab=outline_detail&volumeIndex=${volumeIndex}`);
    },
    [isImportedRewriteProject, project.id, router],
  );

  const editorMaxWidth = getEditorContentMaxWidth(isLeftExpanded, isRightExpanded);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
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
    if (!isImportedRewriteProject && (e.metaKey || e.ctrlKey) && e.key === "j") {
      e.preventDefault();
      handleOpenRewrite();
    }
  }, [handleOpenRewrite, isImportedRewriteProject, toggleLeft, toggleRight]);

  return (
    <>
      <EditorLayout
        isLeftExpanded={isLeftExpanded}
        isRightExpanded={isRightExpanded}
        quickActions={
          <EditorQuickActions
            projectId={project.id}
            projectName={project.name}
            router={router}
            isImportedRewriteProject={isImportedRewriteProject}
            isLeftExpanded={isLeftExpanded}
            leftPanelMode={leftPanelMode}
            toggleLeft={toggleLeft}
            openSettings={openSettings}
          />
        }
        leftPanel={
          <EditorSidePanel
            project={project}
            projectBible={projectBible ?? DEFAULT_BIBLE}
            contentLength={totalContentLength}
            parsedOutline={parsedOutline}
            currentChapter={currentChapter}
            completedChapters={completedChapters}
            onSelectChapter={handleSelectChapter}
            onGenerateBeatsForChapter={handleGenerateBeatsForChapter}
            onCollapse={() => setIsLeftExpanded(false)}
            onFieldChange={undefined}
            onPersistField={persistProjectField}
            onToggleAutoSyncMemory={handleToggleAutoSyncMemory}
            onGoGenerateVolume={handleGoGenerateVolume}
            mode={leftPanelMode}
            hideLengthProgress={isImportedRewriteProject}
            hideCreationControls={isImportedRewriteProject}
          />
        }
        headerLeft={
          <>
            <h1 className="text-lg font-medium">{project.name}</h1>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              {isSaving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>保存中...</span>
                </>
              ) : (
                <span>已保存</span>
              )}
            </div>
            {activeProfileName && (
              <div className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-1.5 text-sm">
                <Sparkles className="w-4 h-4 text-primary" />
                <span className="font-medium">{activeProfileName}</span>
              </div>
            )}
          </>
        }
        headerRight={
          <EditorHeaderActions
            projectId={project.id}
            projectName={project.name}
            isImportedRewriteProject={isImportedRewriteProject}
            selectedChapter={selectedChapterRecord}
            memorySyncSnapshot={memorySyncButtonSnapshot}
            isCheckingMemorySync={isCheckingMemorySync}
            isRewritingSelection={isRewritingSelection}
            isChapterRewriteRunning={isChapterRewriteRunning}
            chaptersCount={chapters.length}
            hasStyleProfile={Boolean(project.style_profile_id)}
            onManualMemorySync={handleManualMemorySync}
            onForceMemorySync={handleForceMemorySync}
            onOpenRewrite={handleOpenRewrite}
            onOpenChapterRewrite={handleOpenSelectedChapterRewrite}
            onOpenChapterRewriteTask={handleOpenChapterRewrite}
            hasChapterRewriteTaskEntry={hasChapterRewriteTaskEntry}
            activeChapterRewriteBatch={activeChapterRewriteBatch}
          />
        }
        chapterBanner={
          <EditorContentBanner
            missingOutlineStatus={missingOutlineStatus}
            selectedVolumeIndex={selectedVolumeIndex}
            isImportedRewriteProject={isImportedRewriteProject}
            hasCurrentChapter={Boolean(currentChapter)}
            hasSelectedChapterRecord={Boolean(selectedChapterRecord)}
            currentVolumeTitle={currentVolumeTitle}
            currentChapterTitle={currentChapterTitle}
            currentChapterStatus={currentChapterStatus}
            onGoGenerateVolume={handleGoGenerateVolume}
            onToggleLeft={toggleLeft}
            onGenerateBeatsForChapter={handleGenerateBeatsForChapter}
          />
        }
        rightPanel={
          isImportedRewriteProject ? null : (
            <BeatPanel
              beats={beatList}
              currentBeatIndex={activeBeatIndex}
              isExpandingBeat={isExpandingBeatProse}
              isGeneratingBeats={isGeneratingBeatPlan}
              onGenerateBeats={handleGenerateBeatPlan}
              onRerunBeatsWorkflow={(feedback) =>
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
          )
        }
        rightPanelToggle={
          <EditorContentRightPanelToggle
            isImportedRewriteProject={isImportedRewriteProject}
            hasSelectedChapter={Boolean(selectedChapterRecord)}
            beatCount={beatList.length}
            activeBeatIndex={activeBeatIndex}
            onToggle={toggleRight}
          />
        }
      >
        <EditorContentTextarea
          textareaRef={textareaRef}
          handleKeyDown={handleKeyDown}
          disabled={!selectedChapterRecord || isRewritingSelection || isExpandingBeatProse || isChapterRewriteRunning || isChapterRewriteApplying}
          placeholder={selectedChapterRecord ? (isImportedRewriteProject ? "编辑导入章节正文..." : "开始创作... 选中文本后按 ⌘J 局部改写") : "请先选择章节..."}
          editorMaxWidth={editorMaxWidth}
        />
      </EditorLayout>

      <EditorContentDialogs
        isImportedRewriteProject={isImportedRewriteProject}
        selectionRewrite={{
          open: isRewriteOpen,
          selectedText: rewriteSelection?.selectedText ?? "",
          instruction: rewriteInstruction,
          preview: rewritePreview,
          isGenerating: isRewritingSelection,
          onInstructionChange: setRewriteInstruction,
          onGenerate: handleGenerateRewritePreview,
          onApply: handleApplyRewritePreview,
          onOpenChange: (open) => {
            if (!open) handleCloseRewrite();
          },
        }}
        chapterRewrite={{
          open: isChapterRewriteOpen,
          chapters: chapterRewriteChapters,
          selectedChapterIds,
          items: chapterRewriteItems,
          activeItem: activeChapterRewriteItem,
          activeChapterId: activeChapterRewriteId,
          instruction: chapterRewriteInstruction,
          expansionRatioPercent: chapterRewriteExpansionRatioPercent,
          batch: activeChapterRewriteBatch,
          isRunning: isChapterRewriteRunning,
          isApplying: isChapterRewriteApplying,
          onInstructionChange: setChapterRewriteInstruction,
          onExpansionRatioPercentChange: setChapterRewriteExpansionRatioPercent,
          onSelectChapter: selectChapterForRewrite,
          onSelectCurrentChapter: selectCurrentChapterForRewrite,
          onSelectAllChapters: selectAllChaptersForRewrite,
          onClearSelectedChapters: clearSelectedChaptersForRewrite,
          onActiveChapterChange: setActiveChapterRewriteId,
          onStart: handleStartChapterRewrite,
          onApplyOne: handleApplyChapterRewrite,
          onApplyAll: handleApplyAllChapterRewrites,
          onOpenChange: (open) => {
            if (!open) handleCloseChapterRewrite();
          },
        }}
        bibleDiff={{
          open: bibleDiff.open,
          currentCharactersStatus: bibleDiff.currentCharactersStatus,
          proposedCharactersStatus: bibleDiff.proposedCharactersStatus,
          currentState: bibleDiff.currentState,
          proposedState: bibleDiff.proposedState,
          currentThreads: bibleDiff.currentThreads,
          proposedThreads: bibleDiff.proposedThreads,
          proposedSummary: bibleDiff.proposedSummary,
          chapterTitle: selectedChapterRecord?.title ?? currentChapterTitle ?? null,
          source: chapterSyncSnapshot?.source ?? null,
          onAccept: acceptRuntimeUpdate,
          onRetry: handleRetryMemoryProposal,
          onDismiss: dismissRuntimeUpdate,
        }}
      />
    </>
  );
}
