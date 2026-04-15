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
  currentBible,
  proposedBible,
  onAccept,
  onDismiss,
}: {
  open: boolean;
  currentBible: string;
  proposedBible: string;
  onAccept: (bible: string) => void;
  onDismiss: () => void;
}) {
  const [editedBible, setEditedBible] = useState(proposedBible);

  // Sync editedBible when proposedBible changes (component stays mounted)
  useEffect(() => {
    setEditedBible(proposedBible);
  }, [proposedBible]);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onDismiss()}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>故事圣经更新提议</DialogTitle>
          <DialogDescription>
            AI 根据本次续写内容提议了故事圣经的更新。你可以直接接受、编辑后接受或忽略。
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 grid grid-cols-2 gap-4 overflow-hidden min-h-0">
          {/* 左：当前 */}
          <div className="flex flex-col overflow-hidden">
            <span className="text-xs font-medium text-muted-foreground mb-2">
              当前内容
            </span>
            <div className="flex-1 overflow-y-auto rounded border border-input bg-muted/30 p-3 text-sm leading-relaxed whitespace-pre-wrap">
              {currentBible || <span className="text-muted-foreground italic">（空）</span>}
            </div>
          </div>

          {/* 右：提议（可编辑） */}
          <div className="flex flex-col overflow-hidden">
            <span className="text-xs font-medium text-muted-foreground mb-2">
              AI 提议（可编辑）
            </span>
            <textarea
              value={editedBible}
              onChange={(e) => setEditedBible(e.target.value)}
              className="flex-1 overflow-y-auto rounded border border-input bg-background p-3 text-sm leading-relaxed resize-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onDismiss}>
            忽略
          </Button>
          <Button onClick={() => onAccept(editedBible)}>
            接受更新
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
