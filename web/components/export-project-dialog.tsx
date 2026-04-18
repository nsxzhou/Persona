"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";

export function ExportProjectDialog({
  projectId,
  projectName,
  triggerButton,
}: {
  projectId: string;
  projectName: string;
  triggerButton?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [isExporting, setIsExporting] = useState<"txt" | "epub" | null>(null);

  const handleExport = async (format: "txt" | "epub") => {
    try {
      setIsExporting(format);
      const blob = await api.exportProject(projectId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = `${projectName}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`项目导出成功 (${format.toUpperCase()})`);
      setOpen(false);
    } catch (err) {
      console.error("Export failed:", err);
      toast.error(`项目导出失败 (${format.toUpperCase()})`);
    } finally {
      setIsExporting(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {triggerButton || (
          <Button variant="outline" onClick={(e) => e.stopPropagation()}>
            <Download className="mr-2 h-4 w-4" />
            导出
          </Button>
        )}
      </DialogTrigger>
      <DialogContent onClick={(e) => e.stopPropagation()}>
        <DialogHeader>
          <DialogTitle>导出项目</DialogTitle>
          <DialogDescription>
            选择您想要导出的文件格式。导出内容将仅包含章节内容的正文。
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4 py-4">
          <Button
            variant="outline"
            size="lg"
            className="w-full justify-start"
            disabled={isExporting !== null}
            onClick={() => handleExport("txt")}
          >
            <Download className="mr-4 h-4 w-4" />
            {isExporting === "txt" ? "正在导出 TXT..." : "导出为 TXT (纯文本)"}
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="w-full justify-start"
            disabled={isExporting !== null}
            onClick={() => handleExport("epub")}
          >
            <Download className="mr-4 h-4 w-4" />
            {isExporting === "epub" ? "正在导出 EPUB..." : "导出为 EPUB (电子书)"}
          </Button>
        </div>
        <DialogFooter className="sm:justify-end">
          <Button variant="ghost" onClick={() => setOpen(false)}>
            取消
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
