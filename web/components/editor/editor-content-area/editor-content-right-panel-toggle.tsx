"use client";

import { ListOrdered } from "lucide-react";

type EditorContentRightPanelToggleProps = {
  isImportedRewriteProject: boolean;
  hasSelectedChapter: boolean;
  beatCount: number;
  activeBeatIndex: number;
  onToggle: () => void;
};

export function EditorContentRightPanelToggle({
  isImportedRewriteProject,
  hasSelectedChapter,
  beatCount,
  activeBeatIndex,
  onToggle,
}: EditorContentRightPanelToggleProps) {
  if (isImportedRewriteProject) {
    return null;
  }

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={!hasSelectedChapter}
      className="motion-button w-12 shrink-0 border-l border-border bg-background flex flex-col items-center pt-3 gap-2 hover:bg-muted/30 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
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
      {beatCount > 0 && (
        <span className="text-[10px] font-semibold text-primary mb-3">
          {Math.max(activeBeatIndex + 1, 1)}/{beatCount}
        </span>
      )}
    </button>
  );
}
