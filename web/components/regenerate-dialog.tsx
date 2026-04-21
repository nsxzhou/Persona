"use client";

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

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

interface RegenerateDialogProps {
  open: boolean;
  title: string;
  description?: string;
  placeholder?: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: (feedback: string) => void;
}

export function RegenerateDialog({
  open,
  title,
  description = "将基于当前稿件重新生成。你可以填写意见指导生成方向（可选）。",
  placeholder = "例如：节奏更紧凑、减少心理描写、保留关键反转…",
  busy = false,
  onCancel,
  onConfirm,
}: RegenerateDialogProps) {
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (open) {
      setFeedback("");
    }
  }, [open]);

  const handleConfirm = () => {
    if (busy) return;
    onConfirm(feedback.trim());
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        if (!value && !busy) onCancel();
      }}
    >
      <DialogContent className="w-[min(520px,92vw)] gap-4">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-primary" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <Textarea
          aria-label="本次生成的意见（可选）"
          placeholder={placeholder}
          rows={5}
          value={feedback}
          disabled={busy}
          onChange={(event) => setFeedback(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
              event.preventDefault();
              handleConfirm();
            }
          }}
        />

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onCancel} disabled={busy}>
            取消
          </Button>
          <Button onClick={handleConfirm} disabled={busy}>
            {busy ? "生成中…" : "重新生成"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
