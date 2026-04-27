"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { ChapterTree } from "@/components/chapter-tree";
import { getProgress, LENGTH_PRESETS, type LengthPresetKey } from "@/lib/length-presets";
import { useDebounceSave } from "@/hooks/use-debounce-save";
import type { ParsedOutline } from "@/lib/outline-parser";
import type { Project, ProjectBible } from "@/lib/types";
import { BIBLE_SECTION_META, type BibleFieldKey } from "@/lib/bible-fields";

export function EditorSidePanel({
  project,
  projectBible,
  contentLength,
  parsedOutline,
  currentChapter,
  completedChapters,
  onSelectChapter,
  onGenerateBeatsForChapter,
  onCollapse,
  onFieldChange,
  onPersistField,
  onToggleAutoSyncMemory,
  onGoGenerateVolume,
  mode = "navigation",
}: {
  project: Project;
  projectBible: ProjectBible;
  contentLength: number;
  parsedOutline: ParsedOutline;
  currentChapter: { volumeIndex: number; chapterIndex: number } | null;
  completedChapters: Set<string>;
  onSelectChapter: (volumeIndex: number, chapterIndex: number) => void;
  onGenerateBeatsForChapter: () => void;
  onCollapse: () => void;
  onFieldChange?: (field: BibleFieldKey, value: string) => void;
  onPersistField?: (field: BibleFieldKey, value: string) => Promise<void>;
  onToggleAutoSyncMemory?: (value: boolean) => void | Promise<void>;
  onGoGenerateVolume?: (volumeIndex: number) => void;
  mode?: "navigation" | "settings";
}) {
  const [fields, setFields] = useState<Record<BibleFieldKey, string>>(() => ({
    description: project.description,
    world_building: projectBible.world_building,
    characters_blueprint: projectBible.characters_blueprint,
    outline_master: projectBible.outline_master,
    outline_detail: projectBible.outline_detail,
    characters_status: projectBible.characters_status,
    runtime_state: projectBible.runtime_state,
    runtime_threads: projectBible.runtime_threads,
  }));

  const isFocusedRef = useRef<Record<string, boolean>>({});

  // 同步外部 props 变更，但不覆盖正在编辑的字段
  useEffect(() => {
    setFields((prev) => ({
      description: isFocusedRef.current["description"] ? prev.description : project.description,
      world_building: isFocusedRef.current["world_building"] ? prev.world_building : projectBible.world_building,
      characters_blueprint: isFocusedRef.current["characters_blueprint"] ? prev.characters_blueprint : projectBible.characters_blueprint,
      outline_master: isFocusedRef.current["outline_master"] ? prev.outline_master : projectBible.outline_master,
      outline_detail: isFocusedRef.current["outline_detail"] ? prev.outline_detail : projectBible.outline_detail,
      characters_status: isFocusedRef.current["characters_status"] ? prev.characters_status : projectBible.characters_status,
      runtime_state: isFocusedRef.current["runtime_state"] ? prev.runtime_state : projectBible.runtime_state,
      runtime_threads: isFocusedRef.current["runtime_threads"] ? prev.runtime_threads : projectBible.runtime_threads,
    }));
  }, [project.description, projectBible.world_building, projectBible.characters_blueprint, projectBible.outline_master, projectBible.outline_detail, projectBible.characters_status, projectBible.runtime_state, projectBible.runtime_threads]);

  const [expandedFields, setExpandedFields] = useState<Set<BibleFieldKey>>(new Set());

  const toggleField = (key: BibleFieldKey) => {
    setExpandedFields((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const debouncedSave = useDebounceSave((field: string, value: string) => {
    if (!onPersistField) return;
    void onPersistField(field as BibleFieldKey, value);
  }, 1500);

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

  const currentChapterTitle = currentChapter
    ? parsedOutline.volumes[currentChapter.volumeIndex]?.chapters[currentChapter.chapterIndex]?.title
    : null;
  const currentVolumeHasChapters = currentChapter
    ? (parsedOutline.volumes[currentChapter.volumeIndex]?.chapters.length ?? 0) > 0
    : true;

  return (
    <aside className="w-[260px] border-r border-border bg-background flex flex-col shrink-0 h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <span className="text-sm font-semibold">
          {mode === "navigation" ? "创作导航" : "创作设定"}
        </span>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onCollapse}>
          <ChevronLeft className="h-4 w-4" />
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

      {mode === "navigation" ? (
        <>
          <div className="flex-1 overflow-y-auto">
            <ChapterTree
              outline={parsedOutline}
              currentChapter={currentChapter}
              completedChapters={completedChapters}
              onSelectChapter={onSelectChapter}
              onGoGenerateVolume={onGoGenerateVolume}
            />
          </div>

          {currentChapterTitle && currentVolumeHasChapters && (
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
        </>
      ) : (
        <div className="flex-1 overflow-y-auto border-t border-border">
          <div className="border-b border-border px-4 py-3 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-medium">自动同步记忆</span>
              <Switch
                checked={project.auto_sync_memory}
                onCheckedChange={(value) => onToggleAutoSyncMemory?.(value)}
                disabled={!onToggleAutoSyncMemory}
                aria-label="自动同步记忆"
              />
            </div>
            <p className="text-[10px] leading-relaxed text-muted-foreground">
              开启后,逐拍写作完成时自动同步记忆,无需手动确认。
            </p>
          </div>
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
                      onFocus={() => { isFocusedRef.current[key] = true; }}
                      onBlur={() => { isFocusedRef.current[key] = false; }}
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
