import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import type { ChapterRewriteItem } from "@/hooks/use-chapter-enrichment-rewrite";
import type { ProjectChapter } from "@/lib/types";
import { cn } from "@/lib/utils";
import { StateBadge } from "./status";

export function ChapterQueue({
  chapters,
  itemByChapterId,
  selectedChapterIds,
  activeChapterId,
  busy,
  onSelectChapter,
  onActiveChapterChange,
  compact,
  simplifyUnselected = false,
}: {
  chapters: ProjectChapter[];
  itemByChapterId: Map<string, ChapterRewriteItem>;
  selectedChapterIds: Set<string>;
  activeChapterId: string | null;
  busy: boolean;
  onSelectChapter: (chapterId: string, checked: boolean) => void;
  onActiveChapterChange: (chapterId: string) => void;
  compact: boolean;
  simplifyUnselected?: boolean;
}) {
  return (
    <div className={cn("space-y-1", compact && "grid gap-1 sm:grid-cols-2 xl:grid-cols-3")}>
      {chapters.map((chapter) => {
        const item = itemByChapterId.get(chapter.id);
        const checked = selectedChapterIds.has(chapter.id);
        const active = activeChapterId === chapter.id;
        const state = item?.state ?? (checked ? "waiting" : null);
        const statusLabel = item?.statusLabel ?? (checked ? "等待生成" : null);
        const checkboxId = `chapter-rewrite-${compact ? "compact" : "setup"}-${chapter.id}`;
        return (
          <div
            key={chapter.id}
            className={cn(
              "rounded-md border px-2.5 py-2 text-sm transition-colors",
              active ? "border-primary/40 bg-primary/10" : "border-transparent hover:bg-muted/60",
            )}
          >
            <div className="flex items-start gap-2">
              <Checkbox
                id={checkboxId}
                checked={checked}
                onCheckedChange={(value) => onSelectChapter(chapter.id, value === true)}
                disabled={busy}
                className="mt-0.5"
              />
              <div className="min-w-0 flex-1">
                <button
                  type="button"
                  className="block min-h-10 w-full text-left"
                  onClick={() => onActiveChapterChange(chapter.id)}
                >
                  <span className="block truncate font-medium">{chapter.title}</span>
                  {statusLabel || !simplifyUnselected ? (
                    <span className="block truncate text-xs text-muted-foreground">
                      {statusLabel ?? "未选择"}
                    </span>
                  ) : null}
                </button>
                <Label htmlFor={checkboxId} className="sr-only">
                  选择 {chapter.title}
                </Label>
              </div>
              {state ? <StateBadge state={state} /> : <span className="text-xs text-muted-foreground">未选</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
