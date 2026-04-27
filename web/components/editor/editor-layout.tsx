"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, BookOpen, Settings, Sparkles, Square, Loader2, ListOrdered } from "lucide-react";
import { useRouter } from "next/navigation";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { EditorNovelMenu } from "@/components/editor-novel-menu";
import { EditorSidePanel } from "@/components/editor-side-panel";
import { ExportProjectDialog } from "@/components/export-project-dialog";
import { Button } from "@/components/ui/button";

export type EditorLayoutProps = {
  projectId: string;
  projectName: string;
  activeProfileName?: string;
  isSaving: boolean;
  isStreamingCompletion: boolean;
  isExpandingBeatProse: boolean;
  isLeftExpanded: boolean;
  isRightExpanded: boolean;
  leftPanelMode: "navigation" | "settings";
  toggleLeft: () => void;
  openSettings: () => void;
  toggleRight: () => void;
  handleStopWrite: () => void;
  handleContinueWrite: () => void;
  missingOutlineStatus: boolean;
  currentVolumeTitle: string | null;
  currentChapterTitle: string | null;
  currentChapterStatus: string;
  chapterBannerAction: React.ReactNode;
  canContinueWrite: boolean;
  memorySyncButton: React.ReactNode;
  workflowRunPanel?: React.ReactNode;
  sidePanelProps: React.ComponentProps<typeof EditorSidePanel>;
  rightPanel: React.ReactNode;
  children: React.ReactNode;
  hasBeats: boolean;
  activeBeatIndex: number;
  totalBeats: number;
  canOpenRightPanel: boolean;
};

export function EditorLayout({
  projectId,
  projectName,
  activeProfileName,
  isSaving,
  isStreamingCompletion,
  isExpandingBeatProse,
  isLeftExpanded,
  isRightExpanded,
  leftPanelMode,
  toggleLeft,
  openSettings,
  toggleRight,
  handleStopWrite,
  handleContinueWrite,
  missingOutlineStatus,
  currentVolumeTitle,
  currentChapterTitle,
  currentChapterStatus,
  chapterBannerAction,
  canContinueWrite,
  memorySyncButton,
  workflowRunPanel,
  sidePanelProps,
  rightPanel,
  children,
  hasBeats,
  activeBeatIndex,
  totalBeats,
  canOpenRightPanel,
}: EditorLayoutProps) {
  const router = useRouter();

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      <div className="w-12 shrink-0 bg-[#111] flex flex-col items-center pt-3 gap-1">
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
      </div>

      <div
        className="shrink-0 overflow-hidden transition-[width] duration-200 ease-in-out flex flex-col"
        style={{ width: isLeftExpanded ? 260 : 0 }}
      >
        <EditorSidePanel {...sidePanelProps} />
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="border-b shrink-0">
          <div className="flex items-center justify-between px-6 py-3">
            <div className="flex items-center gap-4">
              <h1 className="text-lg font-medium">{projectName}</h1>
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
            </div>

            <div className="flex items-center gap-3">
              <ExportProjectDialog projectId={projectId} projectName={projectName} />
              {memorySyncButton}
              {isStreamingCompletion ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleStopWrite}
                  className="gap-2 text-destructive border-destructive/50 hover:bg-destructive/10"
                >
                  <Square className="w-4 h-4" />
                  停止 (Esc)
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleContinueWrite}
                  disabled={!canContinueWrite}
                  className="gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  AI 续写 (⌘J)
                </Button>
              )}
            </div>
          </div>

          <div className="px-6 pb-3">
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
            {workflowRunPanel ? (
              <div className="mt-3">
                {workflowRunPanel}
              </div>
            ) : null}
          </div>
        </header>

        <main className="flex-1 overflow-hidden flex justify-center bg-muted/20">
          {children}
        </main>
      </div>

      {isRightExpanded ? (
        <div
          className="shrink-0 overflow-hidden transition-[width] duration-200 ease-in-out"
          style={{ width: 280 }}
        >
          {rightPanel}
        </div>
      ) : (
        <button
          type="button"
          onClick={toggleRight}
          disabled={!canOpenRightPanel}
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
          {hasBeats && (
            <span className="text-[10px] text-primary font-semibold mb-3">
              {Math.max(activeBeatIndex + 1, 1)}/{totalBeats}
            </span>
          )}
        </button>
      )}
    </div>
  );
}
