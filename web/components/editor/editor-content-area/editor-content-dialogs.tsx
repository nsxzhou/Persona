"use client";

import { ChapterEnrichmentRewriteDialog } from "@/components/editor/chapter-enrichment-rewrite-dialog";
import { SelectionRewriteDialog } from "@/components/editor/selection-rewrite-dialog";
import { BibleDiffDialog } from "@/components/bible-diff-dialog";
import type { ChapterRewriteItem } from "@/hooks/use-chapter-enrichment-rewrite";
import type { ChapterRewriteBatch, ProjectChapter } from "@/lib/types";

type SelectionRewriteDialogState = {
  open: boolean;
  selectedText: string;
  instruction: string;
  preview: string;
  isGenerating: boolean;
  onInstructionChange: (value: string) => void;
  onGenerate: () => void;
  onApply: () => void;
  onOpenChange: (open: boolean) => void;
};

type ChapterRewriteDialogState = {
  open: boolean;
  chapters: ProjectChapter[];
  selectedChapterIds: Set<string>;
  items: ChapterRewriteItem[];
  activeItem: ChapterRewriteItem | null;
  activeChapterId: string | null;
  instruction: string;
  expansionRatioPercent: number;
  batch: ChapterRewriteBatch | null;
  isRunning: boolean;
  isApplying: boolean;
  onInstructionChange: (value: string) => void;
  onExpansionRatioPercentChange: (value: number) => void;
  onSelectChapter: (chapterId: string, checked: boolean) => void;
  onSelectCurrentChapter: () => void;
  onSelectAllChapters: () => void;
  onClearSelectedChapters: () => void;
  onActiveChapterChange: (chapterId: string) => void;
  onStart: () => void;
  onApplyOne: (chapterId: string) => void;
  onApplyAll: () => void;
  onOpenChange: (open: boolean) => void;
};

type BibleDiffDialogState = {
  open: boolean;
  currentCharactersStatus: string;
  proposedCharactersStatus: string;
  currentState: string;
  proposedState: string;
  currentThreads: string;
  proposedThreads: string;
  proposedSummary?: string;
  chapterTitle?: string | null;
  source?: "manual" | "auto" | null;
  onAccept: (charactersStatus: string, state: string, threads: string, summary?: string) => void;
  onRetry?: (feedback: string) => void;
  onDismiss: () => void;
};

type EditorContentDialogsProps = {
  isImportedRewriteProject: boolean;
  selectionRewrite: SelectionRewriteDialogState;
  chapterRewrite: ChapterRewriteDialogState;
  bibleDiff: BibleDiffDialogState;
};

export function EditorContentDialogs({
  isImportedRewriteProject,
  selectionRewrite,
  chapterRewrite,
  bibleDiff,
}: EditorContentDialogsProps) {
  return (
    <>
      {!isImportedRewriteProject ? (
        <SelectionRewriteDialog
          open={selectionRewrite.open}
          selectedText={selectionRewrite.selectedText}
          instruction={selectionRewrite.instruction}
          preview={selectionRewrite.preview}
          isGenerating={selectionRewrite.isGenerating}
          onInstructionChange={selectionRewrite.onInstructionChange}
          onGenerate={selectionRewrite.onGenerate}
          onApply={selectionRewrite.onApply}
          onOpenChange={selectionRewrite.onOpenChange}
        />
      ) : null}

      <ChapterEnrichmentRewriteDialog
        open={chapterRewrite.open}
        chapters={chapterRewrite.chapters}
        selectedChapterIds={chapterRewrite.selectedChapterIds}
        items={chapterRewrite.items}
        activeItem={chapterRewrite.activeItem}
        activeChapterId={chapterRewrite.activeChapterId}
        instruction={chapterRewrite.instruction}
        expansionRatioPercent={chapterRewrite.expansionRatioPercent}
        batch={chapterRewrite.batch}
        isRunning={chapterRewrite.isRunning}
        isApplying={chapterRewrite.isApplying}
        onInstructionChange={chapterRewrite.onInstructionChange}
        onExpansionRatioPercentChange={chapterRewrite.onExpansionRatioPercentChange}
        onSelectChapter={chapterRewrite.onSelectChapter}
        onSelectCurrentChapter={chapterRewrite.onSelectCurrentChapter}
        onSelectAllChapters={chapterRewrite.onSelectAllChapters}
        onClearSelectedChapters={chapterRewrite.onClearSelectedChapters}
        onActiveChapterChange={chapterRewrite.onActiveChapterChange}
        onStart={chapterRewrite.onStart}
        onApplyOne={chapterRewrite.onApplyOne}
        onApplyAll={chapterRewrite.onApplyAll}
        onOpenChange={chapterRewrite.onOpenChange}
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
        chapterTitle={bibleDiff.chapterTitle}
        source={bibleDiff.source}
        onAccept={bibleDiff.onAccept}
        onRetry={bibleDiff.onRetry}
        onDismiss={bibleDiff.onDismiss}
      />
    </>
  );
}
