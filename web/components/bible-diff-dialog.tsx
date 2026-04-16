"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export function BibleDiffDialog({
  open,
  currentState,
  proposedState,
  currentThreads,
  proposedThreads,
  onAccept,
  onDismiss,
}: {
  open: boolean;
  currentState: string;
  proposedState: string;
  currentThreads: string;
  proposedThreads: string;
  onAccept: (state: string, threads: string) => void;
  onDismiss: () => void;
}) {
  const [editedState, setEditedState] = useState(proposedState);
  const [editedThreads, setEditedThreads] = useState(proposedThreads);
  const [activeTab, setActiveTab] = useState<"state" | "threads">("state");

  useEffect(() => {
    setEditedState(proposedState);
    setEditedThreads(proposedThreads);
  }, [proposedState, proposedThreads]);

  const stateChanged = proposedState !== currentState;
  const threadsChanged = proposedThreads !== currentThreads;

  // Default to the tab that has changes
  useEffect(() => {
    if (stateChanged) setActiveTab("state");
    else if (threadsChanged) setActiveTab("threads");
  }, [stateChanged, threadsChanged]);

  const current = activeTab === "state" ? currentState : currentThreads;
  const edited = activeTab === "state" ? editedState : editedThreads;
  const setEdited = activeTab === "state" ? setEditedState : setEditedThreads;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onDismiss()}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>运行时状态更新提议</DialogTitle>
          <DialogDescription>
            AI 根据本次续写内容提议了运行时状态的更新。你可以直接接受、编辑后接受或忽略。
          </DialogDescription>
        </DialogHeader>

        {/* Tabs */}
        <div className="flex gap-1 border-b">
          <button
            type="button"
            onClick={() => setActiveTab("state")}
            className={`px-3 py-1.5 text-sm transition-colors ${
              activeTab === "state"
                ? "border-b-2 border-primary text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            运行时状态
            {stateChanged && <span className="ml-1 text-xs text-primary">*</span>}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("threads")}
            className={`px-3 py-1.5 text-sm transition-colors ${
              activeTab === "threads"
                ? "border-b-2 border-primary text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            伏笔与线索追踪
            {threadsChanged && <span className="ml-1 text-xs text-primary">*</span>}
          </button>
        </div>

        <div className="flex-1 grid grid-cols-2 gap-4 overflow-hidden min-h-0">
          {/* Left: current */}
          <div className="flex flex-col overflow-hidden">
            <span className="text-xs font-medium text-muted-foreground mb-2">
              当前内容
            </span>
            <div className="flex-1 overflow-y-auto rounded border border-input bg-muted/30 p-3 text-sm leading-relaxed whitespace-pre-wrap">
              {current || <span className="text-muted-foreground italic">（空）</span>}
            </div>
          </div>

          {/* Right: proposed (editable) */}
          <div className="flex flex-col overflow-hidden">
            <span className="text-xs font-medium text-muted-foreground mb-2">
              AI 提议（可编辑）
            </span>
            <textarea
              value={edited}
              onChange={(e) => setEdited(e.target.value)}
              className="flex-1 overflow-y-auto rounded border border-input bg-background p-3 text-sm leading-relaxed resize-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onDismiss}>
            忽略
          </Button>
          <Button onClick={() => onAccept(editedState, editedThreads)}>
            接受更新
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
