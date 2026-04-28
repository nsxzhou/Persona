"use client";

import { useEffect, useMemo, useState } from "react";
import { Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

export function ProjectBootstrapDialog({
  open,
  bundleMarkdown,
  busy,
  onApprove,
  onRevise,
  onDismiss,
}: {
  open: boolean;
  bundleMarkdown: string;
  busy: boolean;
  onApprove: () => void;
  onRevise: (editedMarkdown: string) => void;
  onDismiss: () => void;
}) {
  const [edited, setEdited] = useState(bundleMarkdown);

  useEffect(() => {
    if (!open) return;
    setEdited(bundleMarkdown);
  }, [open, bundleMarkdown]);

  const changed = useMemo(() => edited !== bundleMarkdown, [edited, bundleMarkdown]);
  const canRevise = changed && edited.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onDismiss()}>
      <DialogContent className="w-[min(1100px,95vw)] h-[min(860px,92vh)] max-w-none flex flex-col gap-4 p-6">
        <DialogHeader className="space-y-1">
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Wand2 className="h-5 w-5 text-primary" />
            项目初始化审核
          </DialogTitle>
          <DialogDescription>
            AI 已生成世界观、角色与大纲的 Bundle。你可以直接通过，或先编辑再通过。
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-0">
          <Textarea
            value={edited}
            onChange={(e) => setEdited(e.target.value)}
            className="h-full min-h-[520px] resize-none font-mono text-sm leading-relaxed"
            spellCheck={false}
          />
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" onClick={onApprove} disabled={busy}>
            直接通过
          </Button>
          <Button onClick={() => onRevise(edited)} disabled={busy || !canRevise}>
            使用修改版通过
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

