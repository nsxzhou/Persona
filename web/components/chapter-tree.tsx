"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ParsedOutline } from "@/lib/outline-parser";

interface ChapterTreeProps {
  outline: ParsedOutline;
  currentChapter: { volumeIndex: number; chapterIndex: number } | null;
  completedChapters: Set<string>;
  onSelectChapter: (volumeIndex: number, chapterIndex: number) => void;
  onGoGenerateVolume?: (volumeIndex: number) => void;
}

export function ChapterTree({
  outline,
  currentChapter,
  completedChapters,
  onSelectChapter,
  onGoGenerateVolume,
}: ChapterTreeProps) {
  const [collapsedVolumes, setCollapsedVolumes] = useState<Set<number>>(new Set());

  const toggleVolume = (vi: number) => {
    setCollapsedVolumes((prev) => {
      const next = new Set(prev);
      if (next.has(vi)) next.delete(vi);
      else next.add(vi);
      return next;
    });
  };

  if (outline.volumes.length === 0) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-xs text-muted-foreground">
          尚未生成章节细纲。请先在工作台中生成分卷与章节细纲。
        </p>
      </div>
    );
  }

  return (
    <div className="py-2">
      {outline.volumes.map((vol, vi) => {
        const isActiveVolume = currentChapter?.volumeIndex === vi;
        const isCollapsed = collapsedVolumes.has(vi);
        const completedCount = vol.chapters.filter((ch) => completedChapters.has(ch.title)).length;

        return (
          <div key={vi}>
            {/* Volume header */}
            <button
              type="button"
              onClick={() => toggleVolume(vi)}
              className="flex w-full items-center gap-1.5 px-4 py-2 text-left text-xs hover:bg-muted/50 transition-colors"
            >
              {isCollapsed ? (
                <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
              ) : (
                <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
              )}
              <span className="font-semibold text-muted-foreground truncate">{vol.title}</span>
              <span className="ml-auto text-[10px] text-muted-foreground/60 shrink-0">
                {completedCount}/{vol.chapters.length} 章
              </span>
            </button>

            {/* Chapters */}
            {!isCollapsed &&
              vol.chapters.length === 0 && (
                <div className="px-8 py-3 space-y-2 text-xs text-muted-foreground">
                  <p className="font-medium text-foreground">本卷尚未生成章节细纲</p>
                  <p>请先回到「分卷与章节细纲」页为该分卷生成章节细纲</p>
                  {onGoGenerateVolume ? (
                    <button
                      type="button"
                      onClick={() => onGoGenerateVolume(vi)}
                      className="inline-flex items-center rounded-md border border-input px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted"
                    >
                      去生成本卷章节细纲
                    </button>
                  ) : null}
                </div>
              )}
            {!isCollapsed &&
              vol.chapters.length > 0 &&
              vol.chapters.map((ch, ci) => {
                const isActive =
                  currentChapter?.volumeIndex === vi && currentChapter?.chapterIndex === ci;
                const isCompleted = completedChapters.has(ch.title);

                return (
                  <div key={ci}>
                    <button
                      type="button"
                      onClick={() => onSelectChapter(vi, ci)}
                      aria-label={ch.title}
                      className={`flex w-full items-center gap-2 pl-8 pr-4 py-1.5 text-left text-xs transition-colors ${
                        isActive
                          ? "border-l-2 border-primary bg-primary/15 shadow-[inset_0_0_0_1px_rgba(59,130,246,0.18)]"
                          : "hover:bg-muted/30"
                      }`}
                    >
                      {isCompleted ? (
                        <span className="text-emerald-500 shrink-0">✓</span>
                      ) : isActive ? (
                        <span className="text-primary shrink-0">▶</span>
                      ) : (
                        <span className="text-muted-foreground/40 shrink-0">○</span>
                      )}
                      <span
                        className={`truncate ${
                          isCompleted
                            ? "line-through text-muted-foreground/50"
                            : isActive
                              ? "font-semibold text-foreground"
                              : "text-muted-foreground"
                        }`}
                      >
                        {ch.title}
                      </span>
                    </button>

                    {/* Active chapter details */}
                    {isActive && (ch.coreEvent || ch.emotionArc || ch.chapterHook) && (
                      <div className="pl-12 pr-4 py-1.5 space-y-0.5">
                        {ch.coreEvent && (
                          <div className="text-[11px] text-muted-foreground">
                            <span className="text-violet-400">事件：</span>
                            {ch.coreEvent}
                          </div>
                        )}
                        {ch.emotionArc && (
                          <div className="text-[11px] text-muted-foreground">
                            <span className="text-violet-400">情绪：</span>
                            {ch.emotionArc}
                          </div>
                        )}
                        {ch.chapterHook && (
                          <div className="text-[11px] text-muted-foreground">
                            <span className="text-violet-400">钩子：</span>
                            {ch.chapterHook}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        );
      })}
    </div>
  );
}
