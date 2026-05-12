import { ClipboardList, Eye, FileText, Sparkles, Square } from "lucide-react";

import { Button } from "@/components/ui/button";

type OutlineDetailMode = "edit" | "preview" | "generate";

export function OutlineDetailToolbar({
  mode,
  volumeCount,
  totalChapters,
  isGenerating,
  isRawMode,
  onModeChange,
  onInsertTemplate,
  onStopGeneration,
  onGenerateVolumes,
  onToggleRawMode,
}: {
  mode: OutlineDetailMode;
  volumeCount: number;
  totalChapters: number;
  isGenerating: boolean;
  isRawMode: boolean;
  onModeChange: (mode: OutlineDetailMode) => void;
  onInsertTemplate: () => void;
  onStopGeneration: () => void;
  onGenerateVolumes: () => void;
  onToggleRawMode: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">
          分卷与章节细纲
        </span>
        <span className="text-xs text-muted-foreground/50">
          · {volumeCount} 卷 · {totalChapters} 章
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex overflow-hidden rounded-md border border-border">
          <button
            type="button"
            onClick={() => onModeChange("edit")}
            className={`px-3 py-1 text-xs transition-colors ${
              mode !== "preview"
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            编辑
          </button>
          <button
            type="button"
            onClick={() => onModeChange("preview")}
            className={`px-3 py-1 text-xs transition-colors ${
              mode === "preview"
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            预览
          </button>
        </div>

        <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={onInsertTemplate}>
          <ClipboardList className="h-3.5 w-3.5" />
          模板
        </Button>

        {isGenerating ? (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 border-destructive/30 text-xs text-destructive"
            onClick={onStopGeneration}
          >
            <Square className="h-3.5 w-3.5" />
            停止
          </Button>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 border-green-600/30 text-xs text-green-600 hover:bg-green-600/10"
            onClick={onGenerateVolumes}
          >
            <Sparkles className="h-3.5 w-3.5" />
            AI 生成
          </Button>
        )}

        <Button variant="ghost" size="sm" className="gap-1.5 text-xs" onClick={onToggleRawMode}>
          {isRawMode ? <Eye className="h-3.5 w-3.5" /> : <FileText className="h-3.5 w-3.5" />}
          {isRawMode ? "返回结构化视图" : "编辑原始 Markdown"}
        </Button>
      </div>
    </div>
  );
}
