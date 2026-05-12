import { useCallback, useEffect, useMemo, useRef, type KeyboardEvent } from "react";
import { useEditorContext, useEditorStore } from "./editor-context";
import type { EditorState } from "./editor-store";
import { useShallow } from "zustand/react/shallow";
import { useEditorAutosave } from "@/hooks/use-editor-autosave";
import { useSelectionRewrite } from "@/hooks/use-selection-rewrite";
import { useBeatGeneration } from "@/hooks/use-beat-generation";
import { useChapterEnrichmentRewrite } from "@/hooks/use-chapter-enrichment-rewrite";
import { useChapterMemorySync } from "@/hooks/use-chapter-memory-sync";
import { parseOutline } from "@/lib/outline-parser";
import { useProjectQuery, useProjectBibleQuery } from "@/hooks/use-project-query";
import { useChaptersQuery } from "@/hooks/use-chapters-query";
import { useQueryClient } from "@tanstack/react-query";
import { EditorLayout } from "./editor-layout";
import { BibleDiffDialog } from "@/components/bible-diff-dialog";
import { BeatPanel } from "@/components/beat-panel";
import { Sparkles, Loader2, ListOrdered } from "lucide-react";
import { EditorSidePanel } from "@/components/editor-side-panel";
import { SelectionRewriteDialog } from "@/components/editor/selection-rewrite-dialog";
import { ChapterEnrichmentRewriteDialog } from "@/components/editor/chapter-enrichment-rewrite-dialog";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { ProjectBible } from "@/lib/types";
import { DEFAULT_BIBLE } from "./editor-defaults";
import { EditorHeaderActions, EditorQuickActions } from "./editor-header-actions";
import { useEditorPersistence } from "./editor-persistence";
import { EditorTextarea } from "./editor-textarea";
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

  const chapterBannerAction = missingOutlineStatus && selectedVolumeIndex !== null && !isImportedRewriteProject ? (
    <Button variant="outline" size="sm" onClick={() => handleGoGenerateVolume(selectedVolumeIndex)}>
      去生成本卷章节细纲
    </Button>
  ) : currentChapter && selectedChapterRecord && !isImportedRewriteProject ? (
    <div className="flex flex-wrap justify-end gap-2">
      <Button variant="outline" className="gap-2" size="sm" onClick={handleGenerateBeatsForChapter}>
        <Sparkles className="h-4 w-4" />
        生成节拍
      </Button>
    </div>
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
          <div className="flex flex-col gap-3 rounded-md border border-border bg-muted/30 px-4 py-3 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                当前章节
              </p>
              {missingOutlineStatus ? (
                <>
                  <p className="text-sm font-medium text-foreground">当前分卷尚未生成章节细纲</p>
                  <p className="text-xs text-muted-foreground">
                    请先回到「分卷与章节细纲」页为该分卷生成章节细纲
                  </p>
                </>
              ) : currentChapterTitle ? (
                <>
                  <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                    <span>{currentVolumeTitle}</span>
                    <span>/</span>
                    <span className="font-medium text-foreground">{currentChapterTitle}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{currentChapterStatus}</p>
                </>
              ) : (
                <>
                  <p className="text-sm font-medium text-foreground">未选择章节</p>
                  <p className="text-xs text-muted-foreground">{currentChapterStatus}</p>
                </>
              )}
            </div>
            <div className="flex shrink-0 flex-col gap-2 md:items-end">
              <div>{chapterBannerAction}</div>
            </div>
          </div>
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
          isImportedRewriteProject ? null : (
            <button
              type="button"
              onClick={toggleRight}
              disabled={!Boolean(selectedChapterRecord)}
              className="w-12 shrink-0 border-l border-border bg-background flex flex-col items-center pt-3 gap-2 hover:bg-muted/30 transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
              title="展开节拍写作 (⌘⇧J)"
            >
              <ListOrdered className="h-[18px] w-[18px] text-muted-foreground" />
              <span
                className="text-[10px] text-muted-foreground tracking-widest mt-2"
                style={{ writingMode: "vertical-rl" }}
              >
                节拍写作
              </span>
              <div className="flex-1" />
              {beatList.length > 0 && (
                <span className="text-[10px] text-primary font-semibold mb-3">
                  {Math.max(activeBeatIndex + 1, 1)}/{beatList.length}
                </span>
              )}
            </button>
          )
        }
      >
        <EditorTextarea
          ref={textareaRef}
          handleKeyDown={handleKeyDown}
          disabled={!selectedChapterRecord || isRewritingSelection || isExpandingBeatProse || isChapterRewriteRunning || isChapterRewriteApplying}
          placeholder={selectedChapterRecord ? (isImportedRewriteProject ? "编辑导入章节正文..." : "开始创作... 选中文本后按 ⌘J 局部改写") : "请先选择章节..."}
          className={`w-full ${editorMaxWidth} h-full p-8 md:p-12 resize-none bg-transparent outline-none text-lg leading-relaxed shadow-none border-none focus:ring-0 text-foreground/90 placeholder:text-muted-foreground/50 disabled:cursor-not-allowed`}
        />
      </EditorLayout>

      {!isImportedRewriteProject ? (
        <SelectionRewriteDialog
          open={isRewriteOpen}
          selectedText={rewriteSelection?.selectedText ?? ""}
          instruction={rewriteInstruction}
          preview={rewritePreview}
          isGenerating={isRewritingSelection}
          onInstructionChange={setRewriteInstruction}
          onGenerate={handleGenerateRewritePreview}
          onApply={handleApplyRewritePreview}
          onOpenChange={(open) => {
            if (!open) handleCloseRewrite();
          }}
        />
      ) : null}

      <ChapterEnrichmentRewriteDialog
        open={isChapterRewriteOpen}
        chapters={chapterRewriteChapters}
        selectedChapterIds={selectedChapterIds}
        items={chapterRewriteItems}
        activeItem={activeChapterRewriteItem}
        activeChapterId={activeChapterRewriteId}
        instruction={chapterRewriteInstruction}
        expansionRatioPercent={chapterRewriteExpansionRatioPercent}
        batch={activeChapterRewriteBatch}
        isRunning={isChapterRewriteRunning}
        isApplying={isChapterRewriteApplying}
        onInstructionChange={setChapterRewriteInstruction}
        onExpansionRatioPercentChange={setChapterRewriteExpansionRatioPercent}
        onSelectChapter={selectChapterForRewrite}
        onSelectCurrentChapter={selectCurrentChapterForRewrite}
        onSelectAllChapters={selectAllChaptersForRewrite}
        onClearSelectedChapters={clearSelectedChaptersForRewrite}
        onActiveChapterChange={setActiveChapterRewriteId}
        onStart={handleStartChapterRewrite}
        onApplyOne={handleApplyChapterRewrite}
        onApplyAll={handleApplyAllChapterRewrites}
        onOpenChange={(open) => {
          if (!open) handleCloseChapterRewrite();
        }}
      />

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
