"use client";

import { useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ParsedOutline } from "@/lib/outline-parser";
import { useVirtualizer } from "@tanstack/react-virtual";

interface ChapterTreeProps {
  outline: ParsedOutline;
  currentChapter: { volumeIndex: number; chapterIndex: number } | null;
  completedChapters: Set<string>;
  onSelectChapter: (volumeIndex: number, chapterIndex: number) => void;
  onGoGenerateVolume?: (volumeIndex: number) => void;
}

type FlatItem =
  | { type: "volume"; vi: number; vol: ParsedOutline["volumes"][0] }
  | { type: "empty-volume"; vi: number; vol: ParsedOutline["volumes"][0] }
  | { type: "chapter"; vi: number; ci: number; ch: any }
  | { type: "chapter-details"; vi: number; ci: number; ch: any };

function estimateItemSize(item: FlatItem) {
  if (item.type === "volume") return 36;
  if (item.type === "empty-volume") return 120;
  if (item.type === "chapter") return 28;
  if (item.type === "chapter-details") {
    let lines = 0;
    if (item.ch.coreEvent) lines++;
    if (item.ch.emotionArc) lines++;
    if (item.ch.chapterHook) lines++;
    return 12 + lines * 20;
  }
  return 35;
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

  const flatItems = useMemo(() => {
    const items: FlatItem[] = [];
    outline.volumes.forEach((vol, vi) => {
      items.push({ type: "volume", vi, vol });
      if (!collapsedVolumes.has(vi)) {
        if (vol.chapters.length === 0) {
          items.push({ type: "empty-volume", vi, vol });
        } else {
          vol.chapters.forEach((ch, ci) => {
            items.push({ type: "chapter", vi, ci, ch });
            const isActive = currentChapter?.volumeIndex === vi && currentChapter?.chapterIndex === ci;
            if (isActive && (ch.coreEvent || ch.emotionArc || ch.chapterHook)) {
              items.push({ type: "chapter-details", vi, ci, ch });
            }
          });
        }
      }
    });
    return items;
  }, [outline, collapsedVolumes, currentChapter]);

  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: flatItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => {
      return estimateItemSize(flatItems[index]);
    },
    overscan: 10,
  });
  const virtualItems = rowVirtualizer.getVirtualItems();
  const renderedRows = virtualItems.length > 0
    ? virtualItems
    : flatItems.map((item, index) => ({
        index,
        key: `fallback-${index}`,
        size: estimateItemSize(item),
        start: flatItems.slice(0, index).reduce((sum, previous) => sum + estimateItemSize(previous), 0),
      }));
  const totalHeight = Math.max(
    rowVirtualizer.getTotalSize(),
    flatItems.reduce((sum, item) => sum + estimateItemSize(item), 0),
  );

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
    <div ref={parentRef} className="h-full w-full overflow-y-auto py-2">
      <div
        style={{
          height: `${totalHeight}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {renderedRows.map((virtualRow) => {
          const item = flatItems[virtualRow.index];
          const { vi } = item;

          return (
            <div
              key={virtualRow.key}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              {item.type === "volume" && (
                <button
                  type="button"
                  onClick={() => toggleVolume(vi)}
                  className="flex w-full items-center gap-1.5 px-4 py-2 text-left text-xs hover:bg-muted/50 transition-colors h-[36px]"
                >
                  {collapsedVolumes.has(vi) ? (
                    <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
                  ) : (
                    <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
                  )}
                  <span className="font-semibold text-muted-foreground truncate">{item.vol.title}</span>
                  <span className="ml-auto text-[10px] text-muted-foreground/60 shrink-0">
                    {item.vol.chapters.filter((ch) => completedChapters.has(ch.title)).length}/{item.vol.chapters.length} 章
                  </span>
                </button>
              )}

              {item.type === "empty-volume" && (
                <div className="px-8 py-3 space-y-2 text-xs text-muted-foreground h-[120px]">
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

              {item.type === "chapter" && (
                <button
                  type="button"
                  onClick={() => onSelectChapter(vi, item.ci)}
                  aria-label={item.ch.title}
                  className={`flex w-full items-center gap-2 pl-8 pr-4 py-1.5 text-left text-xs transition-colors h-[28px] ${
                    currentChapter?.volumeIndex === vi && currentChapter?.chapterIndex === item.ci
                      ? "border-l-2 border-primary bg-primary/15 shadow-[inset_0_0_0_1px_rgba(59,130,246,0.18)]"
                      : "hover:bg-muted/30"
                  }`}
                >
                  {completedChapters.has(item.ch.title) ? (
                    <span className="text-emerald-500 shrink-0">✓</span>
                  ) : currentChapter?.volumeIndex === vi && currentChapter?.chapterIndex === item.ci ? (
                    <span className="text-primary shrink-0">▶</span>
                  ) : (
                    <span className="text-muted-foreground/40 shrink-0">○</span>
                  )}
                  <span
                    className={`truncate ${
                      completedChapters.has(item.ch.title)
                        ? "line-through text-muted-foreground/50"
                        : currentChapter?.volumeIndex === vi && currentChapter?.chapterIndex === item.ci
                          ? "font-semibold text-foreground"
                          : "text-muted-foreground"
                    }`}
                  >
                    {item.ch.title}
                  </span>
                </button>
              )}

              {item.type === "chapter-details" && (
                <div className="pl-12 pr-4 py-1.5 space-y-0.5 h-full overflow-hidden">
                  {item.ch.coreEvent && (
                    <div className="text-[11px] text-muted-foreground truncate">
                      <span className="text-violet-400">事件：</span>
                      {item.ch.coreEvent}
                    </div>
                  )}
                  {item.ch.emotionArc && (
                    <div className="text-[11px] text-muted-foreground truncate">
                      <span className="text-violet-400">情绪：</span>
                      {item.ch.emotionArc}
                    </div>
                  )}
                  {item.ch.chapterHook && (
                    <div className="text-[11px] text-muted-foreground truncate">
                      <span className="text-violet-400">钩子：</span>
                      {item.ch.chapterHook}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
