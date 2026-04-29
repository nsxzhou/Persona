"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type SelectionRewriteDialogProps = {
  open: boolean;
  selectedText: string;
  instruction: string;
  preview: string;
  isGenerating: boolean;
  onInstructionChange: (value: string) => void;
  onGenerate: () => void;
  onApply: () => void;
  onOpenChange: (open: boolean) => void;
};

export function SelectionRewriteDialog({
  open,
  selectedText,
  instruction,
  preview,
  isGenerating,
  onInstructionChange,
  onGenerate,
  onApply,
  onOpenChange,
}: SelectionRewriteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>局部改写</DialogTitle>
          <DialogDescription>
            输入修改要求，生成预览后再替换当前选区。
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <section className="space-y-2">
            <Label>原选区</Label>
            <div className="max-h-40 overflow-auto rounded-md border border-border bg-muted/30 p-3 text-sm leading-relaxed whitespace-pre-wrap">
              {selectedText}
            </div>
          </section>

          <section className="space-y-2">
            <Label htmlFor="selection-rewrite-instruction">修改要求</Label>
            <Textarea
              id="selection-rewrite-instruction"
              value={instruction}
              onChange={(event) => onInstructionChange(event.target.value)}
              placeholder="例如：加强压迫感，减少解释，保留原意。"
              disabled={isGenerating}
            />
          </section>

          <section className="space-y-2">
            <Label>改写预览</Label>
            <div className="min-h-32 max-h-64 overflow-auto rounded-md border border-border bg-background p-3 text-sm leading-relaxed whitespace-pre-wrap">
              {preview || "生成后在这里预览改写结果。"}
            </div>
          </section>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isGenerating}>
            取消
          </Button>
          <Button variant="outline" onClick={onGenerate} disabled={isGenerating}>
            {isGenerating ? "生成中..." : "生成改写"}
          </Button>
          <Button onClick={onApply} disabled={isGenerating || !preview.trim()}>
            替换选区
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
