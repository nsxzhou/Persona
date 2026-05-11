"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  CircleDot,
  GitCompareArrows,
  Loader2,
  ListChecks,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { ChapterRewriteItem } from "@/hooks/use-chapter-enrichment-rewrite";
import type { ChapterRewriteBatch } from "@/lib/types";
import {
  computeLineDiff,
  groupDiffBlocks,
  summarizeDiff,
  type DiffBlock,
} from "@/lib/diff-utils";
import type { ProjectChapter } from "@/lib/types";
import { cn } from "@/lib/utils";

type ChapterEnrichmentRewriteDialogProps = {
  open: boolean;
  chapters: ProjectChapter[];
  selectedChapterIds: Set<string>;
  items: ChapterRewriteItem[];
  activeItem: ChapterRewriteItem | null;
  activeChapterId: string | null;
  instruction: string;
  batch: ChapterRewriteBatch | null;
  isRunning: boolean;
  isApplying: boolean;
  onInstructionChange: (value: string) => void;
  onSelectChapter: (chapterId: string, checked: boolean) => void;
  onActiveChapterChange: (chapterId: string) => void;
  onStart: () => void;
  onApplyOne: (chapterId: string) => void;
  onApplyAll: () => void;
  onOpenChange: (open: boolean) => void;
};

const STATE_LABEL: Record<ChapterRewriteItem["state"], string> = {
  waiting: "等待",
  running: "运行中",
  generated: "已生成",
  failed: "失败",
  applying: "应用中",
  applied: "已应用",
  apply_failed: "应用失败",
};

const STATE_TONE: Record<ChapterRewriteItem["state"], string> = {
  waiting: "border-border bg-muted/30 text-muted-foreground",
  running: "border-blue-200 bg-blue-50 text-blue-800",
  generated: "border-emerald-200 bg-emerald-50 text-emerald-800",
  failed: "border-red-200 bg-red-50 text-red-800",
  applying: "border-blue-200 bg-blue-50 text-blue-800",
  applied: "border-slate-200 bg-slate-50 text-slate-600",
  apply_failed: "border-red-200 bg-red-50 text-red-800",
};

export function ChapterEnrichmentRewriteDialog({
  open,
  chapters,
  selectedChapterIds,
  items,
  activeItem,
  activeChapterId,
  instruction,
  batch,
  isRunning,
  isApplying,
  onInstructionChange,
  onSelectChapter,
  onActiveChapterChange,
  onStart,
  onApplyOne,
  onApplyAll,
  onOpenChange,
}: ChapterEnrichmentRewriteDialogProps) {
  const hasGeneratedPreview = items.some((item) => item.preview.trim() && item.state !== "applied");
  const hasFailure = items.some((item) => item.state === "failed" || item.state === "apply_failed");
  const [manualPhase, setManualPhase] = useState<"setup" | "progress" | "review">(
    hasGeneratedPreview || hasFailure ? "review" : "setup",
  );
  const [showQueue, setShowQueue] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [onlyChanges, setOnlyChanges] = useState(false);
  const hasReviewSignalRef = useRef(hasGeneratedPreview || hasFailure);
  const busy = isRunning || isApplying;
  const batchComplete = Boolean(batch && batch.status !== "pending" && batch.status !== "running");
  const phase = isRunning ? "progress" : batchComplete ? "review" : manualPhase;
  const itemByChapterId = new Map(items.map((item) => [item.chapter.id, item]));
  const generatedCount = items.filter((item) => item.preview.trim() && item.state !== "applied").length;
  const selectedCount = selectedChapterIds.size;
  const appliedCount = items.filter((item) => item.state === "applied").length;
  const failedCount = items.filter((item) => item.state === "failed" || item.state === "apply_failed").length;
  const runningItem = items.find((item) => item.state === "running") ?? null;
  const activeItemIndex = activeItem
    ? items.findIndex((item) => item.chapter.id === activeItem.chapter.id)
    : -1;
  const reviewPosition = activeItemIndex >= 0 ? activeItemIndex + 1 : 0;
  const canGoPrevious = activeItemIndex > 0;
  const canGoNext = activeItemIndex >= 0 && activeItemIndex < items.length - 1;
  const logsVisible = showLogs || Boolean(activeItem?.errorMessage || activeItem?.applyErrorMessage);
  const currentContent = activeItem?.chapter.content ?? "";
  const previewContent = activeItem?.preview ?? "";
  const hasPreview = previewContent.trim().length > 0;
  const activeDiff = useMemo(
    () => computeLineDiff(currentContent, hasPreview ? previewContent : currentContent),
    [currentContent, hasPreview, previewContent],
  );
  const activeStats = useMemo(() => summarizeDiff(activeDiff), [activeDiff]);
  const leftBlocks = useMemo(
    () =>
      groupDiffBlocks(
        activeDiff.filter((line) =>
          onlyChanges ? line.type === "removed" : line.type !== "added",
        ),
      ),
    [activeDiff, onlyChanges],
  );
  const rightBlocks = useMemo(
    () =>
      groupDiffBlocks(
        activeDiff.filter((line) =>
          onlyChanges ? line.type === "added" : line.type !== "removed",
        ),
      ),
    [activeDiff, onlyChanges],
  );
  const logContent =
    activeItem?.errorMessage ||
    activeItem?.applyErrorMessage ||
    activeItem?.logs ||
    "任务日志会显示在这里。";

  useEffect(() => {
    const hasReviewSignal = hasGeneratedPreview || hasFailure;
    if (hasReviewSignal && !hasReviewSignalRef.current) {
      setManualPhase("review");
    }
    if (!hasReviewSignal && !isRunning) {
      setManualPhase("setup");
      setShowQueue(false);
      setShowLogs(false);
    }
    hasReviewSignalRef.current = hasReviewSignal;
  }, [hasFailure, hasGeneratedPreview, isRunning]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[min(860px,92vh)] w-[min(1320px,94vw)] max-w-none flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b py-4 pl-6 pr-14">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 space-y-1">
              <DialogTitle className="flex items-center gap-2 text-xl">
                <GitCompareArrows className="h-5 w-5 text-primary" />
                改写章节
              </DialogTitle>
              <DialogDescription>
                {phase === "setup"
                  ? "先填写改写要求并选择章节，生成后进入差异审核。"
                  : phase === "progress"
                    ? "任务在后台顺序改写章节，关闭窗口不会中断。"
                  : "逐章检查左右差异，确认后再替换正文。"}
              </DialogDescription>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              <StatusPill
                label={phase === "setup" ? "已选" : "进度"}
                value={phase === "setup" ? selectedCount : (batch?.generated_count ?? generatedCount) + (batch?.failed_count ?? failedCount)}
                suffix={phase === "setup" ? undefined : `/${batch?.total_count ?? items.length}`}
              />
              <StatusPill label="可应用" value={generatedCount} tone={generatedCount > 0 ? "success" : "neutral"} />
              {failedCount > 0 ? <StatusPill label="失败" value={failedCount} tone="danger" /> : null}
              {appliedCount > 0 ? <StatusPill label="已应用" value={appliedCount} /> : null}
            </div>
          </div>
        </DialogHeader>

        {phase === "setup" ? (
          <section className="flex flex-1 overflow-hidden bg-muted/10 px-5 py-5">
            <div className="grid min-h-0 w-full gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
              <aside className="flex min-h-0 flex-col overflow-hidden rounded-md border bg-background">
                <div className="flex items-center justify-between border-b px-3.5 py-3">
                  <Label>选择章节</Label>
                  <span className="text-xs text-muted-foreground">{selectedCount}/{chapters.length}</span>
                </div>
                <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
                  <ChapterQueue
                    chapters={chapters}
                    itemByChapterId={itemByChapterId}
                    selectedChapterIds={selectedChapterIds}
                    activeChapterId={activeChapterId}
                    busy={busy}
                    onSelectChapter={onSelectChapter}
                    onActiveChapterChange={onActiveChapterChange}
                    compact={false}
                    simplifyUnselected
                  />
                </div>
              </aside>

              <div className="flex min-h-0 flex-col rounded-md border bg-background">
                <div className="flex min-h-0 flex-1 flex-col gap-3 p-5">
                  <div className="space-y-1.5">
                    <Label htmlFor="chapter-enrichment-instruction" className="text-base font-semibold">
                      自由改写要求
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      写清本次批量改写的目标、保留边界和禁止事项。
                    </p>
                  </div>
                  <Textarea
                    id="chapter-enrichment-instruction"
                    value={instruction}
                    onChange={(event) => onInstructionChange(event.target.value)}
                    placeholder="例如：增强情绪张力和动作细节，保留剧情事实，不要续写下一章。"
                    disabled={busy}
                    className="min-h-[360px] flex-1 resize-none text-base leading-7 shadow-none"
                  />
                  <p className="text-sm text-muted-foreground">
                    运行期间会锁定改写要求与章节选择，生成完成后自动进入差异审核。
                  </p>
                </div>
              </div>
            </div>
          </section>
        ) : phase === "progress" ? (
          <section className="flex min-h-0 flex-1 overflow-hidden bg-muted/10 px-5 py-5">
            <div className="grid min-h-0 w-full gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
              <aside className="flex min-h-0 flex-col overflow-hidden rounded-md border bg-background">
                <div className="flex items-center justify-between border-b px-3.5 py-3">
                  <Label>章节队列</Label>
                  <span className="text-xs text-muted-foreground">
                    {batch?.generated_count ?? generatedCount}/{batch?.total_count ?? items.length}
                  </span>
                </div>
                <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
                  <ChapterQueue
                    chapters={chapters}
                    itemByChapterId={itemByChapterId}
                    selectedChapterIds={selectedChapterIds}
                    activeChapterId={activeChapterId}
                    busy={busy}
                    onSelectChapter={onSelectChapter}
                    onActiveChapterChange={onActiveChapterChange}
                    compact={false}
                    simplifyUnselected={false}
                  />
                </div>
              </aside>
              <div className="flex min-h-0 flex-col rounded-md border bg-background">
                <div className="border-b p-5">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold">
                        {runningItem?.chapter.title ?? batch?.current_chapter_title ?? "等待 worker 接手"}
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {batch?.stage ?? runningItem?.statusLabel ?? "pending"}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <StatusPill label="总数" value={batch?.total_count ?? items.length} />
                      <StatusPill label="已生成" value={batch?.generated_count ?? generatedCount} tone="success" />
                      <StatusPill label="失败" value={batch?.failed_count ?? failedCount} tone={failedCount > 0 ? "danger" : "neutral"} />
                    </div>
                  </div>
                </div>
                <div className="min-h-0 flex-1 p-5">
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{
                        width: `${Math.min(
                          100,
                          Math.round(
                            (((batch?.generated_count ?? generatedCount) + (batch?.failed_count ?? failedCount)) /
                              Math.max(batch?.total_count ?? items.length, 1)) *
                              100,
                          ),
                        )}%`,
                      }}
                    />
                  </div>
                  <div className="mt-5 rounded-md border bg-muted/20 p-3 text-xs leading-relaxed whitespace-pre-wrap">
                    {logContent}
                  </div>
                </div>
              </div>
            </div>
          </section>
        ) : (
          <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="border-b px-5 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => activeItemIndex >= 0 && onActiveChapterChange(items[activeItemIndex - 1].chapter.id)}
                    disabled={!canGoPrevious || busy}
                    aria-label="上一章"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <div className="min-w-0">
                    <p className="truncate text-base font-semibold">
                      {activeItem?.chapter.title ?? "请选择章节"}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {activeItem
                        ? `${activeItemIndex + 1}/${items.length} · ${STATE_LABEL[activeItem.state]} · 原文 ${activeItem.chapter.word_count} 字`
                        : "运行后显示章节状态"}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => activeItemIndex >= 0 && onActiveChapterChange(items[activeItemIndex + 1].chapter.id)}
                    disabled={!canGoNext || busy}
                    aria-label="下一章"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1 rounded-full border bg-background px-2.5 py-1">
                    <span className="font-medium text-foreground">本章</span>
                    <span className="text-emerald-700">+{activeStats.added}</span>
                    <span className="text-red-700">-{activeStats.removed}</span>
                  </span>
                  <label className="inline-flex items-center gap-2">
                    <Switch checked={onlyChanges} onCheckedChange={setOnlyChanges} />
                    <span>只看改动</span>
                  </label>
                  <Button type="button" variant="ghost" size="sm" onClick={() => setShowQueue((value) => !value)}>
                    <ListChecks className="mr-2 h-4 w-4" />
                    章节队列
                  </Button>
                </div>
              </div>

              {showQueue ? (
                <div className="mt-3 max-h-44 overflow-y-auto rounded-md border bg-background p-2">
                  <ChapterQueue
                    chapters={chapters}
                    itemByChapterId={itemByChapterId}
                    selectedChapterIds={selectedChapterIds}
                    activeChapterId={activeChapterId}
                    busy={busy}
                    onSelectChapter={onSelectChapter}
                    onActiveChapterChange={onActiveChapterChange}
                    compact
                    simplifyUnselected={false}
                  />
                </div>
              ) : null}
            </div>

            <div className="grid min-h-0 flex-1 gap-3 overflow-hidden p-5 xl:grid-cols-2">
              <DiffColumn
                title="当前正文"
                blocks={leftBlocks}
                side="left"
                empty={!activeItem || currentContent === ""}
                emptyText={activeItem ? "当前章节正文为空。" : "请选择章节后查看当前正文。"}
              />
              <DiffColumn
                title="AI 改写预览"
                blocks={rightBlocks}
                side="right"
                empty={!activeItem || previewContent === ""}
                emptyText={
                  activeItem
                    ? activeItem.state === "running"
                      ? "正在生成改写预览。"
                      : "任务成功后在这里显示 AI 改写正文。"
                    : "请选择章节后查看改写预览。"
                }
              />
            </div>

            <div className="border-t px-5 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  <button
                    type="button"
                    className="rounded-md px-2 py-1 text-primary hover:bg-primary/10"
                    onClick={() => setShowLogs((value) => !value)}
                  >
                    {logsVisible ? "隐藏日志" : hasFailure ? "查看错误" : "查看日志"}
                  </button>
                  <span className="inline-flex items-center gap-1 text-amber-800">
                    <AlertCircle className="h-3.5 w-3.5" />
                    应用会直接替换正文，不保留旧版本。
                  </span>
                </div>
                <Button
                  variant="outline"
                  onClick={() => activeItem && onApplyOne(activeItem.chapter.id)}
                  disabled={busy || !batchComplete || !activeItem?.preview.trim() || activeItem.state === "applied" || activeItem.state === "failed"}
                >
                  应用当前
                </Button>
              </div>
              {logsVisible ? (
                <div className="mt-3 max-h-28 overflow-auto rounded-md border bg-muted/20 p-3 text-xs leading-relaxed whitespace-pre-wrap">
                  {logContent}
                </div>
              ) : null}
            </div>
          </section>
        )}

        <DialogFooter className="border-t px-6 py-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            关闭
          </Button>
          {phase === "review" && !busy && !batch ? (
            <Button variant="ghost" onClick={() => setManualPhase("setup")}>
              返回配置
            </Button>
          ) : null}
          {phase === "setup" ? (
            <Button variant="outline" onClick={onStart} disabled={busy || !instruction.trim() || selectedChapterIds.size === 0 || Boolean(batch)}>
              {isRunning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  运行中
                </>
              ) : (
                "开始改写"
              )}
            </Button>
          ) : null}
          {phase === "setup" && hasGeneratedPreview ? (
            <Button variant="outline" onClick={() => setManualPhase("review")}>
              查看预览
            </Button>
          ) : null}
          {batchComplete && phase === "progress" ? (
            <Button variant="outline" onClick={() => setManualPhase("review")}>
              审核结果
            </Button>
          ) : null}
          <Button onClick={onApplyAll} disabled={busy || !batchComplete || generatedCount === 0}>
            {isApplying ? "应用中..." : "应用全部预览"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function StatusPill({
  label,
  value,
  suffix,
  tone = "neutral",
}: {
  label: string;
  value: number;
  suffix?: string;
  tone?: "neutral" | "success" | "danger";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1",
        tone === "success" && "border-emerald-200 bg-emerald-50 text-emerald-800",
        tone === "danger" && "border-red-200 bg-red-50 text-red-800",
        tone === "neutral" && "border-border bg-muted/40 text-muted-foreground",
      )}
    >
      <span>{label}</span>
      <span className="font-semibold tabular-nums text-foreground">{value}{suffix}</span>
    </span>
  );
}

function ChapterQueue({
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

function StateBadge({ state }: { state: ChapterRewriteItem["state"] }) {
  const Icon =
    state === "generated" || state === "applied"
      ? CheckCircle2
      : state === "failed" || state === "apply_failed"
        ? AlertCircle
        : state === "running" || state === "applying"
          ? Loader2
          : CircleDot;
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        STATE_TONE[state],
      )}
    >
      <Icon
        className={cn(
          "h-3 w-3",
          (state === "running" || state === "applying") && "animate-spin",
        )}
      />
      {STATE_LABEL[state]}
    </span>
  );
}

function DiffColumn({
  title,
  blocks,
  side,
  empty,
  emptyText,
}: {
  title: string;
  blocks: DiffBlock[];
  side: "left" | "right";
  empty: boolean;
  emptyText: string;
}) {
  return (
    <div className="flex min-h-0 flex-col overflow-hidden rounded-md border bg-background">
      <div className="border-b px-3 py-2">
        <span className="text-xs font-medium text-muted-foreground">{title}</span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto bg-muted/20 p-3 font-mono text-sm leading-relaxed">
        {empty ? (
          <span className="text-muted-foreground italic">{emptyText}</span>
        ) : (
          <DiffBlocks blocks={blocks} side={side} />
        )}
      </div>
    </div>
  );
}

function DiffBlocks({ blocks, side }: { blocks: DiffBlock[]; side: "left" | "right" }) {
  return (
    <div className="whitespace-pre-wrap break-words">
      {blocks.map((block, index) =>
        block.lines.map((line, lineIndex) => (
          <DiffLineRow
            key={`${index}-${lineIndex}`}
            type={line.type}
            text={line.text}
            hideAdded={side === "left"}
            hideRemoved={side === "right"}
          />
        )),
      )}
    </div>
  );
}

function DiffLineRow({
  type,
  text,
  hideAdded,
  hideRemoved,
}: {
  type: "added" | "removed" | "unchanged";
  text: string;
  hideAdded?: boolean;
  hideRemoved?: boolean;
}) {
  if (type === "added" && hideAdded) return null;
  if (type === "removed" && hideRemoved) return null;
  const marker = type === "added" ? "+" : type === "removed" ? "-" : " ";
  return (
    <div
      className={cn(
        "flex gap-2 px-1",
        type === "added" && "bg-emerald-500/15 text-emerald-800",
        type === "removed" && "bg-red-500/15 text-red-800 line-through",
      )}
    >
      <span className="select-none text-muted-foreground">{marker}</span>
      <span className="flex-1">{text || " "}</span>
    </div>
  );
}
