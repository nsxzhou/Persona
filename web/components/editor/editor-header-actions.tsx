import { ArrowLeft, BookOpen, GitCompareArrows, Settings, Sparkles } from "lucide-react";

import { ExportProjectDialog } from "@/components/export-project-dialog";
import { MemorySyncButton } from "@/components/memory-sync-button";
import { EditorNovelMenu } from "@/components/editor-novel-menu";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { ProjectChapter } from "@/lib/types";

import type { EditorState } from "./editor-store";
import type { toMemorySyncButtonSnapshot } from "./use-editor-memory-actions";

type MemorySyncButtonSnapshot = ReturnType<typeof toMemorySyncButtonSnapshot>;

export function EditorQuickActions({
  projectId,
  projectName,
  router,
  isImportedRewriteProject,
  isLeftExpanded,
  leftPanelMode,
  toggleLeft,
  openSettings,
}: {
  projectId: string;
  projectName: string;
  router: { push: (href: string) => void };
  isImportedRewriteProject: boolean;
  isLeftExpanded: boolean;
  leftPanelMode: EditorState["leftPanelMode"];
  toggleLeft: () => void;
  openSettings: () => void;
}) {
  return (
    <>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="default"
            size="icon"
            className="w-8 h-8 rounded-none mb-3 hover:opacity-90 transition-opacity"
            title="快速导航"
          >
            <span className="font-black text-sm">P</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent side="right" align="start" className="w-64 p-0">
          <EditorNovelMenu projectId={projectId} projectName={projectName} />
        </PopoverContent>
      </Popover>

      <Button
        variant="ghost"
        size="icon"
        onClick={toggleLeft}
        className={`w-9 h-9 rounded-none transition-colors ${
          isLeftExpanded && leftPanelMode === "navigation" ? "bg-white/15" : "hover:bg-white/10"
        }`}
        title="创作导航 (⌘B)"
      >
        <BookOpen className="h-[18px] w-[18px] text-white" />
      </Button>

      {!isImportedRewriteProject ? (
        <Button
          variant="ghost"
          size="icon"
          onClick={openSettings}
          className={`w-9 h-9 rounded-none transition-colors ${
            isLeftExpanded && leftPanelMode === "settings" ? "bg-white/15" : "opacity-50 hover:opacity-80"
          }`}
          title="创作设定"
        >
          <Settings className="h-[18px] w-[18px] text-white" />
        </Button>
      ) : null}

      <div className="flex-1" />

      <Button
        variant="ghost"
        size="icon"
        onClick={() => router.push(`/projects/${projectId}`)}
        className="w-9 h-9 rounded-none opacity-50 hover:opacity-80 transition-opacity mb-3"
        title="返回项目工作台"
      >
        <ArrowLeft className="h-[18px] w-[18px] text-white" />
      </Button>
    </>
  );
}

export function EditorHeaderActions({
  projectId,
  projectName,
  isImportedRewriteProject,
  selectedChapter,
  memorySyncSnapshot,
  isCheckingMemorySync,
  isRewritingSelection,
  isChapterRewriteRunning,
  chaptersCount,
  hasStyleProfile,
  onManualMemorySync,
  onForceMemorySync,
  onOpenRewrite,
  onOpenChapterRewrite,
  onOpenChapterRewriteTask,
  hasChapterRewriteTaskEntry,
  activeChapterRewriteBatch,
}: {
  projectId: string;
  projectName: string;
  isImportedRewriteProject: boolean;
  selectedChapter: ProjectChapter | null;
  memorySyncSnapshot: MemorySyncButtonSnapshot;
  isCheckingMemorySync: boolean;
  isRewritingSelection: boolean;
  isChapterRewriteRunning: boolean;
  chaptersCount: number;
  hasStyleProfile: boolean;
  onManualMemorySync: () => void;
  onForceMemorySync: () => void;
  onOpenRewrite: () => void;
  onOpenChapterRewrite: () => void;
  onOpenChapterRewriteTask: () => void;
  hasChapterRewriteTaskEntry: boolean;
  activeChapterRewriteBatch: {
    generated_count: number;
    failed_count: number;
    total_count: number;
  } | null;
}) {
  return (
    <>
      <ExportProjectDialog projectId={projectId} projectName={projectName} />
      {!isImportedRewriteProject ? (
        <>
          <MemorySyncButton
            snapshot={memorySyncSnapshot}
            isChecking={isCheckingMemorySync}
            disabled={!selectedChapter}
            onClick={onManualMemorySync}
            onForceRerun={onForceMemorySync}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenRewrite}
            disabled={!Boolean(hasStyleProfile && selectedChapter) || isRewritingSelection || isChapterRewriteRunning}
            className="gap-2"
          >
            <Sparkles className="w-4 h-4" />
            局部改写 (⌘J)
          </Button>
        </>
      ) : null}
      <Button
        variant="outline"
        size="sm"
        onClick={onOpenChapterRewrite}
        disabled={chaptersCount === 0}
        className="gap-2"
      >
        <Sparkles className="w-4 h-4" />
        {isImportedRewriteProject ? "改写章节" : "章节润色"}
      </Button>
      {hasChapterRewriteTaskEntry && activeChapterRewriteBatch ? (
        <Button
          variant="secondary"
          size="sm"
          onClick={onOpenChapterRewriteTask}
          className="gap-2"
        >
          <GitCompareArrows className="h-4 w-4" />
          改写任务 {activeChapterRewriteBatch.generated_count + activeChapterRewriteBatch.failed_count}/{activeChapterRewriteBatch.total_count}
        </Button>
      ) : null}
    </>
  );
}
