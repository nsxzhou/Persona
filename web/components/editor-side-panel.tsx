"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Sparkles, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ChapterTree } from "@/components/chapter-tree";
import { api } from "@/lib/api";
import { getProgress, LENGTH_PRESETS, type LengthPresetKey } from "@/lib/length-presets";
import type { ParsedOutline } from "@/lib/outline-parser";
import type { Project } from "@/lib/types";
import { BIBLE_SECTION_META, type BibleFieldKey } from "@/lib/bible-fields";

export function EditorSidePanel({
  project,
  contentLength,
  parsedOutline,
  currentChapter,
  completedChapters,
  onSelectChapter,
  onGenerateBeatsForChapter,
  onClose,
  onFieldChange,
}: {
  project: Project;
  contentLength: number;
  parsedOutline: ParsedOutline;
  currentChapter: { volumeIndex: number; chapterIndex: number } | null;
  completedChapters: Set<string>;
  onSelectChapter: (volumeIndex: number, chapterIndex: number) => void;
  onGenerateBeatsForChapter: () => void;
  onClose: () => void;
  onFieldChange?: (field: BibleFieldKey, value: string) => void;
}) {
  const [fields, setFields] = useState<Record<BibleFieldKey, string>>(() => ({
    inspiration: project.inspiration,
    world_building: project.world_building,
    characters: project.characters,
    outline_master: project.outline_master,
    outline_detail: project.outline_detail,
    story_bible: project.story_bible,
  }));

  useEffect(() => {
    setFields({
      inspiration: project.inspiration,
      world_building: project.world_building,
      characters: project.characters,
      outline_master: project.outline_master,
      outline_detail: project.outline_detail,
      story_bible: project.story_bible,
    });
  }, [project.inspiration, project.world_building, project.characters, project.outline_master, project.outline_detail, project.story_bible]);

  const [bibleExpanded, setBibleExpanded] = useState(false);
  const [expandedFields, setExpandedFields] = useState<Set<BibleFieldKey>>(new Set());
  const saveTimers = useRef<Record<string, NodeJS.Timeout>>({});

  const toggleField = (key: BibleFieldKey) => {
    setExpandedFields((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const debouncedSave = useCallback(
    (field: string, value: string) => {
      if (saveTimers.current[field]) clearTimeout(saveTimers.current[field]);
      saveTimers.current[field] = setTimeout(async () => {
        try {
          await api.updateProject(project.id, { [field]: value });
        } catch {
          toast.error("保存失败");
        }
      }, 1500);
    },
    [project.id],
  );

  useEffect(() => {
    const timers = saveTimers.current;
    return () => Object.values(timers).forEach(clearTimeout);
  }, []);

  const handleChange = (key: BibleFieldKey, value: string) => {
    setFields((prev) => ({ ...prev, [key]: value }));
    debouncedSave(key, value);
    onFieldChange?.(key, value);
  };

  const presetKey = (project.length_preset || "short") as LengthPresetKey;
  const presetCfg = LENGTH_PRESETS[presetKey];
  const progress = getProgress(contentLength, presetKey);

  const progressColor =
    progress.phase === "over_target"
      ? "text-red-500"
      : progress.phase === "ending_zone"
        ? "text-amber-500"
        : "text-emerald-500";

  const progressBarColor =
    progress.phase === "over_target"
      ? "bg-red-500"
      : progress.phase === "ending_zone"
        ? "bg-amber-500"
        : "bg-emerald-500";

  const phaseLabel =
    progress.phase === "over_target"
      ? "已超出目标"
      : progress.phase === "ending_zone"
        ? "进入收束"
        : null;

  // Current chapter info for the action button
  const currentChapterTitle = currentChapter
    ? parsedOutline.volumes[currentChapter.volumeIndex]?.chapters[currentChapter.chapterIndex]?.title
    : null;

  return (
    <aside className="w-80 border-l border-border bg-background flex flex-col shrink-0 h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <span className="text-sm font-semibold">创作导航</span>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Progress bar */}
      <div className="px-4 py-3 border-b border-border shrink-0 space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">{presetCfg.label}</span>
          <span className={progressColor}>
            {contentLength.toLocaleString()} / {(presetCfg.targetMin / 10000)}-{(presetCfg.targetMax / 10000)}万字
            {" · "}{progress.percentage}%
            {phaseLabel && <span className="ml-1 font-medium">{` · ${phaseLabel}`}</span>}
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${progressBarColor}`}
            style={{ width: `${Math.min(progress.percentage, 100)}%` }}
          />
        </div>
      </div>

      {/* Chapter Tree — main scrollable area */}
      <div className="flex-1 overflow-y-auto">
        <ChapterTree
          outline={parsedOutline}
          currentChapter={currentChapter}
          completedChapters={completedChapters}
          onSelectChapter={onSelectChapter}
        />
      </div>

      {/* Current chapter action */}
      {currentChapterTitle && (
        <div className="border-t border-border p-3 space-y-1.5 shrink-0">
          <Button
            className="w-full gap-2"
            size="sm"
            onClick={onGenerateBeatsForChapter}
          >
            <Sparkles className="h-3.5 w-3.5" />
            为当前章节生成节拍
          </Button>
          <p className="text-[10px] text-center text-muted-foreground truncate">
            {currentChapterTitle}
          </p>
        </div>
      )}

      {/* Divider */}
      <div className="border-t border-border shrink-0" />

      {/* Bible fields — collapsible section */}
      <div className="shrink-0">
        <button
          type="button"
          onClick={() => setBibleExpanded(!bibleExpanded)}
          className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs hover:bg-muted/50 transition-colors"
        >
          {bibleExpanded ? (
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3 w-3 text-muted-foreground" />
          )}
          <span className="font-semibold text-muted-foreground">创作设定</span>
        </button>
      </div>

      {bibleExpanded && (
        <div className="overflow-y-auto max-h-[300px] border-t border-border">
          {BIBLE_SECTION_META.map(({ key, title }) => {
            const isOpen = expandedFields.has(key);
            const text = fields[key];
            return (
              <div key={key} className="border-b border-border last:border-b-0">
                <button
                  type="button"
                  onClick={() => toggleField(key)}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs hover:bg-muted/50 transition-colors"
                >
                  {isOpen ? (
                    <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
                  ) : (
                    <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
                  )}
                  <span className="font-medium truncate">{title}</span>
                  {!isOpen && text.trim() && (
                    <span className="ml-auto text-[10px] text-muted-foreground shrink-0">
                      {text.trim().length} 字
                    </span>
                  )}
                </button>
                {isOpen && (
                  <div className="px-4 pb-2">
                    <textarea
                      value={text}
                      onChange={(e) => handleChange(key, e.target.value)}
                      className="w-full min-h-[80px] resize-y rounded border border-input bg-background px-2 py-1.5 text-xs leading-relaxed placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      placeholder={`编辑${title}...`}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </aside>
  );
}
