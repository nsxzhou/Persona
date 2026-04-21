"use client";

import { useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  ChevronRight,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RegenerateDialog } from "@/components/regenerate-dialog";

export function BeatPanel({
  beats,
  currentBeatIndex,
  isExpandingBeat,
  isGeneratingBeats,
  onGenerateBeats,
  onRegenerateBeats,
  onRegenerateExpansion,
  onBeatsChange,
  onStartExpand,
  onClose,
  disabled = false,
  hasChapterContent = false,
}: {
  beats: string[];
  currentBeatIndex: number;
  isExpandingBeat: boolean;
  isGeneratingBeats: boolean;
  onGenerateBeats: () => void;
  onRegenerateBeats?: (feedback: string) => void;
  onRegenerateExpansion?: (feedback: string) => void;
  onBeatsChange: (beats: string[]) => void;
  onStartExpand: () => void;
  onClose: () => void;
  disabled?: boolean;
  hasChapterContent?: boolean;
}) {
  const [newBeat, setNewBeat] = useState("");
  const [regenerateMode, setRegenerateMode] = useState<"beats" | "expansion" | null>(null);

  const moveBeat = (index: number, dir: -1 | 1) => {
    const target = index + dir;
    if (target < 0 || target >= beats.length) return;
    const next = [...beats];
    [next[index], next[target]] = [next[target], next[index]];
    onBeatsChange(next);
  };

  const removeBeat = (index: number) => {
    onBeatsChange(beats.filter((_, i) => i !== index));
  };

  const updateBeat = (index: number, value: string) => {
    const next = [...beats];
    next[index] = value;
    onBeatsChange(next);
  };

  const addBeat = () => {
    if (!newBeat.trim()) return;
    onBeatsChange([...beats, newBeat.trim()]);
    setNewBeat("");
  };

  const handleRegenerateConfirm = (feedback: string) => {
    if (regenerateMode === "beats") {
      onRegenerateBeats?.(feedback);
    } else if (regenerateMode === "expansion") {
      onRegenerateExpansion?.(feedback);
    }
    setRegenerateMode(null);
  };

  const handlePrimaryBeatClick = () => {
    if (beats.length > 0 && onRegenerateBeats) {
      setRegenerateMode("beats");
      return;
    }
    onGenerateBeats();
  };

  return (
    <aside className="w-full border-l border-border bg-background flex flex-col shrink-0 h-full overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <span className="text-sm font-semibold">节拍写作</span>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {beats.length === 0 && !isGeneratingBeats && (
          <p className="text-xs text-muted-foreground text-center py-4">
            {disabled
              ? "请先选择一个章节，再使用节拍写作。"
              : "点击下方「生成节拍」按钮，AI 将根据大纲和前文为你规划节拍。"}
          </p>
        )}

        {beats.map((beat, i) => (
          <div
            key={i}
            className={`flex items-start gap-2 rounded-md p-2 text-sm transition-colors ${
              i === currentBeatIndex && isExpandingBeat
                ? "bg-primary/10 ring-1 ring-primary"
                : i < currentBeatIndex && currentBeatIndex >= 0
                  ? "opacity-50"
                  : "bg-muted/30"
            }`}
          >
            <span className="text-xs text-muted-foreground font-mono mt-1.5 shrink-0 w-5 text-right">
              {i + 1}
            </span>
            <Input
              value={beat}
              onChange={(e) => updateBeat(i, e.target.value)}
              className="flex-1 h-auto py-1 text-xs border-none shadow-none focus-visible:ring-0 bg-transparent"
              disabled={isExpandingBeat}
            />
            {!isExpandingBeat && (
              <div className="flex flex-col gap-0.5 shrink-0">
                <button
                  type="button"
                  onClick={() => moveBeat(i, -1)}
                  disabled={i === 0}
                  className="text-muted-foreground hover:text-foreground disabled:opacity-30"
                >
                  <ArrowUp className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  onClick={() => moveBeat(i, 1)}
                  disabled={i === beats.length - 1}
                  className="text-muted-foreground hover:text-foreground disabled:opacity-30"
                >
                  <ArrowDown className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  onClick={() => removeBeat(i)}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            )}
          </div>
        ))}

        {/* 添加节拍 */}
        {!isExpandingBeat && beats.length > 0 && (
          <div className="flex gap-2 pt-1">
            <Input
              value={newBeat}
              onChange={(e) => setNewBeat(e.target.value)}
              placeholder="添加节拍..."
              className="flex-1 h-8 text-xs"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addBeat();
                }
              }}
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-2"
              onClick={addBeat}
              disabled={!newBeat.trim()}
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>

      {/* 底部操作 */}
      <div className="border-t border-border p-3 space-y-2 shrink-0">
        {beats.length === 0 || !isExpandingBeat ? (
          <Button
            className="w-full gap-2"
            size="sm"
            onClick={handlePrimaryBeatClick}
            disabled={disabled || isGeneratingBeats}
          >
            {isGeneratingBeats ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {beats.length > 0 ? "重新生成节拍" : "生成节拍"}
          </Button>
        ) : null}
        {beats.length > 0 && !isExpandingBeat && (
          <Button
            className="w-full gap-2"
            size="sm"
            variant="secondary"
            onClick={onStartExpand}
            disabled={disabled}
          >
            <Play className="h-4 w-4" />
            开始逐拍写作
          </Button>
        )}
        {beats.length > 0
          && hasChapterContent
          && !isExpandingBeat
          && onRegenerateExpansion && (
          <Button
            className="w-full gap-2"
            size="sm"
            variant="outline"
            onClick={() => setRegenerateMode("expansion")}
            disabled={disabled}
          >
            <RefreshCw className="h-4 w-4" />
            带意见重写本章正文
          </Button>
        )}
        {isExpandingBeat && (
          <p className="text-xs text-center text-muted-foreground">
            正在展开第 {currentBeatIndex + 1}/{beats.length} 拍...
          </p>
        )}
      </div>

      <RegenerateDialog
        open={regenerateMode !== null}
        title={regenerateMode === "expansion" ? "重写本章正文" : "重新生成节拍"}
        description={
          regenerateMode === "expansion"
            ? "将在保留现有节拍的基础上，按你的意见重写本章正文。意见可填可不填。"
            : "将基于当前节拍列表重新生成。你可以填写意见指导生成方向（可选）。"
        }
        busy={isGeneratingBeats || isExpandingBeat}
        onCancel={() => setRegenerateMode(null)}
        onConfirm={handleRegenerateConfirm}
      />
    </aside>
  );
}
