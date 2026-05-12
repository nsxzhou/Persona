"use client";

import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

type EditorContentBannerProps = {
  missingOutlineStatus: boolean;
  selectedVolumeIndex: number | null;
  isImportedRewriteProject: boolean;
  hasCurrentChapter: boolean;
  hasSelectedChapterRecord: boolean;
  currentVolumeTitle: string | null;
  currentChapterTitle: string | null;
  currentChapterStatus: string | null;
  onGoGenerateVolume: (volumeIndex: number) => void;
  onToggleLeft: () => void;
  onGenerateBeatsForChapter: () => void;
};

export function EditorContentBanner({
  missingOutlineStatus,
  selectedVolumeIndex,
  isImportedRewriteProject,
  hasCurrentChapter,
  hasSelectedChapterRecord,
  currentVolumeTitle,
  currentChapterTitle,
  currentChapterStatus,
  onGoGenerateVolume,
  onToggleLeft,
  onGenerateBeatsForChapter,
}: EditorContentBannerProps) {
  const action =
    missingOutlineStatus && selectedVolumeIndex !== null && !isImportedRewriteProject ? (
      <Button variant="outline" size="sm" onClick={() => onGoGenerateVolume(selectedVolumeIndex)}>
        去生成本卷章节细纲
      </Button>
    ) : hasCurrentChapter && hasSelectedChapterRecord && !isImportedRewriteProject ? (
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="outline" className="gap-2" size="sm" onClick={onGenerateBeatsForChapter}>
          <Sparkles className="h-4 w-4" />
          生成节拍
        </Button>
      </div>
    ) : (
      <Button variant="outline" size="sm" onClick={onToggleLeft}>
        打开创作导航
      </Button>
    );

  return (
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
        <div>{action}</div>
      </div>
    </div>
  );
}
