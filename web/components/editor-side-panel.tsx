"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { BIBLE_SECTION_META, type BibleFieldKey } from "@/lib/bible-fields";

export function EditorSidePanel({
  project,
  onClose,
  onFieldChange,
}: {
  project: Project;
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

  // Sync local fields when project prop changes (e.g., after bible update acceptance)
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
  const [expanded, setExpanded] = useState<Set<BibleFieldKey>>(new Set());
  const saveTimers = useRef<Record<string, NodeJS.Timeout>>({});

  const toggle = (key: BibleFieldKey) => {
    setExpanded((prev) => {
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

  return (
    <aside className="w-80 border-l border-border bg-background flex flex-col shrink-0 h-full overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <span className="text-sm font-semibold">创作设定</span>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {BIBLE_SECTION_META.map(({ key, title }) => {
          const isOpen = expanded.has(key);
          const text = fields[key];
          return (
            <div key={key} className="border-b border-border last:border-b-0">
              <button
                type="button"
                onClick={() => toggle(key)}
                className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm hover:bg-muted/50 transition-colors"
              >
                {isOpen ? (
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                )}
                <span className="font-medium truncate">{title}</span>
                {!isOpen && text.trim() && (
                  <span className="ml-auto text-xs text-muted-foreground shrink-0">
                    {text.trim().length} 字
                  </span>
                )}
              </button>
              {isOpen && (
                <div className="px-4 pb-3">
                  <textarea
                    value={text}
                    onChange={(e) => handleChange(key, e.target.value)}
                    className="w-full min-h-[100px] resize-y rounded border border-input bg-background px-2 py-1.5 text-xs leading-relaxed placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    placeholder={`编辑${title}...`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
