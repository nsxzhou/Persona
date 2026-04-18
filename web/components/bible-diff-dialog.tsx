"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { FileClock, GitCompareArrows } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import {
  computeLineDiff,
  groupDiffBlocks,
  summarizeDiff,
  type DiffBlock,
} from "@/lib/diff-utils";

type TabKey = "state" | "threads";

type SourceLabel = "manual" | "auto" | null;

interface BibleDiffDialogProps {
  open: boolean;
  currentState: string;
  proposedState: string;
  currentThreads: string;
  proposedThreads: string;
  chapterTitle?: string | null;
  source?: SourceLabel;
  onAccept: (state: string, threads: string) => void;
  onRetry?: () => void;
  onDismiss: () => void;
}

export function BibleDiffDialog({
  open,
  currentState,
  proposedState,
  currentThreads,
  proposedThreads,
  chapterTitle,
  source,
  onAccept,
  onRetry,
  onDismiss,
}: BibleDiffDialogProps) {
  const [editedState, setEditedState] = useState(proposedState);
  const [editedThreads, setEditedThreads] = useState(proposedThreads);
  const [activeTab, setActiveTab] = useState<TabKey>("state");
  const [onlyChanges, setOnlyChanges] = useState(false);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    setEditedState(proposedState);
    setEditedThreads(proposedThreads);
    setEditing(false);
  }, [proposedState, proposedThreads]);

  const stateChanged = proposedState !== currentState;
  const threadsChanged = proposedThreads !== currentThreads;

  useEffect(() => {
    if (stateChanged) setActiveTab("state");
    else if (threadsChanged) setActiveTab("threads");
  }, [stateChanged, threadsChanged]);

  const current = activeTab === "state" ? currentState : currentThreads;
  const edited = activeTab === "state" ? editedState : editedThreads;
  const setEdited = activeTab === "state" ? setEditedState : setEditedThreads;

  const diff = useDebouncedDiff(current, edited);
  const stats = useMemo(() => summarizeDiff(diff), [diff]);

  const totalStats = useMemo(() => {
    const stateDiff = computeLineDiff(currentState, editedState);
    const threadsDiff = computeLineDiff(currentThreads, editedThreads);
    const stateSum = summarizeDiff(stateDiff);
    const threadsSum = summarizeDiff(threadsDiff);
    return {
      added: stateSum.added + threadsSum.added,
      removed: stateSum.removed + threadsSum.removed,
    };
  }, [currentState, editedState, currentThreads, editedThreads]);

  const changeCount = stats.added + stats.removed;

  const leftBlocks = useMemo(
    () =>
      groupDiffBlocks(
        diff.filter((line) =>
          onlyChanges ? line.type === "removed" : line.type !== "added",
        ),
        { collapseUnchanged: onlyChanges },
      ),
    [diff, onlyChanges],
  );
  const rightBlocks = useMemo(
    () =>
      groupDiffBlocks(
        diff.filter((line) =>
          onlyChanges ? line.type === "added" : line.type !== "removed",
        ),
        { collapseUnchanged: onlyChanges },
      ),
    [diff, onlyChanges],
  );

  const sourceText = formatSource(source ?? null, chapterTitle);

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onDismiss()}>
      <DialogContent
        className="flex flex-col w-[min(1280px,95vw)] h-[min(860px,92vh)] max-w-none gap-4 p-6"
      >
        <DialogHeader className="space-y-1">
          <DialogTitle className="flex items-center gap-2 text-lg">
            <GitCompareArrows className="h-5 w-5 text-primary" />
            运行时记忆更新确认
          </DialogTitle>
          <DialogDescription>
            AI 根据本次续写内容提议了运行时状态的更新。你可以直接接受、编辑后接受或忽略。
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3">
          <div className="flex gap-1">
            <TabButton
              active={activeTab === "state"}
              onClick={() => {
                setActiveTab("state");
                setEditing(false);
              }}
              label="运行时状态"
              changed={stateChanged}
            />
            <TabButton
              active={activeTab === "threads"}
              onClick={() => {
                setActiveTab("threads");
                setEditing(false);
              }}
              label="伏笔与线索追踪"
              changed={threadsChanged}
            />
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-muted/40 px-2.5 py-1">
              <span className="font-medium text-foreground">本页变更 {changeCount} 行</span>
              <span className="text-emerald-600">+{stats.added}</span>
              <span className="text-red-600">-{stats.removed}</span>
            </span>
            <span className="text-muted-foreground">
              本次提议共 {totalStats.added + totalStats.removed} 行变更
            </span>
            <label className="inline-flex items-center gap-2">
              <Switch checked={onlyChanges} onCheckedChange={setOnlyChanges} />
              <span>只看改动</span>
            </label>
          </div>
        </div>

        <div className="flex-1 grid grid-cols-2 gap-4 overflow-hidden min-h-0">
          <DiffColumn
            title="当前内容"
            blocks={leftBlocks}
            side="left"
            empty={current === ""}
          />

          <div className="flex flex-col overflow-hidden">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">
                AI 提议（可编辑）
              </span>
              <button
                type="button"
                onClick={() => setEditing((value) => !value)}
                className="text-xs text-primary hover:underline"
              >
                {editing ? "返回预览" : "编辑原文"}
              </button>
            </div>
            {editing ? (
              <textarea
                value={edited}
                onChange={(e) => setEdited(e.target.value)}
                className="flex-1 overflow-y-auto rounded border border-input bg-background p-3 text-sm leading-relaxed resize-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring font-mono"
              />
            ) : (
              <DiffColumn
                title=""
                blocks={rightBlocks}
                side="right"
                empty={edited === ""}
                inline
              />
            )}
          </div>
        </div>

        <DialogFooter className="flex flex-col items-start gap-3 border-t pt-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <FileClock className="h-3.5 w-3.5" />
            {sourceText}
          </p>
          <div className="flex gap-2 self-end">
            <Button variant="ghost" onClick={onDismiss}>
              忽略
            </Button>
            {onRetry ? (
              <Button variant="outline" onClick={onRetry}>
                重新生成
              </Button>
            ) : null}
            <Button size="default" onClick={() => onAccept(editedState, editedThreads)}>
              接受更新
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function TabButton({
  active,
  onClick,
  label,
  changed,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  changed: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm transition-colors",
        active
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-muted hover:text-foreground",
      )}
    >
      <span>{label}</span>
      {changed && <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
    </button>
  );
}

function DiffColumn({
  title,
  blocks,
  side,
  empty,
  inline,
}: {
  title: string;
  blocks: DiffBlock[];
  side: "left" | "right";
  empty: boolean;
  inline?: boolean;
}) {
  return (
    <div className={cn("flex flex-col overflow-hidden", !inline && "gap-2")}>
      {title && (
        <span className="text-xs font-medium text-muted-foreground">{title}</span>
      )}
      <div className="flex-1 overflow-y-auto rounded border border-input bg-muted/20 p-3 font-mono text-sm leading-relaxed min-h-0">
        {empty ? (
          <span className="text-muted-foreground italic">（空）</span>
        ) : (
          <DiffBlocks blocks={blocks} side={side} />
        )}
      </div>
    </div>
  );
}

function DiffBlocks({ blocks, side }: { blocks: DiffBlock[]; side: "left" | "right" }) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  return (
    <div className="whitespace-pre-wrap break-words">
      {blocks.map((block, index) => {
        if (block.type === "unchanged-collapsed") {
          const isOpen = expanded[index];
          return (
            <div key={index}>
              <button
                type="button"
                onClick={() =>
                  setExpanded((value) => ({ ...value, [index]: !value[index] }))
                }
                className="my-1 w-full rounded bg-muted px-2 py-1 text-left text-[11px] text-muted-foreground hover:bg-muted/70"
              >
                {isOpen ? "收起" : `展开 ${block.collapsedCount ?? block.lines.length} 行未变更`}
              </button>
              {isOpen &&
                block.lines.map((line, lineIndex) => (
                  <DiffLineRow key={lineIndex} type="unchanged" text={line.text} />
                ))}
            </div>
          );
        }
        return block.lines.map((line, lineIndex) => (
          <DiffLineRow
            key={`${index}-${lineIndex}`}
            type={line.type}
            text={line.text}
            hideAdded={side === "left"}
            hideRemoved={side === "right"}
          />
        ));
      })}
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

function formatSource(source: SourceLabel, chapterTitle?: string | null): string {
  const sourceName = source === "manual" ? "手动触发" : source === "auto" ? "续写后自动" : "未知来源";
  if (chapterTitle) return `来源：${chapterTitle} · ${sourceName}`;
  return `来源：${sourceName}`;
}

function useDebouncedDiff(current: string, edited: string) {
  const [diff, setDiff] = useState(() => computeLineDiff(current, edited));
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDiff(computeLineDiff(current, edited));
    }, 100);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [current, edited]);
  return diff;
}
