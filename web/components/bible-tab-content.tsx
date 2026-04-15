"use client";

import { useState } from "react";
import {
  ClipboardList,
  Loader2,
  Sparkles,
  Square,
} from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { MarkdownPreview } from "@/components/markdown-preview";
import type { BibleFieldKey } from "@/lib/bible-fields";
import { BIBLE_TEMPLATES } from "@/lib/bible-templates";

interface BibleTabContentProps {
  fieldKey: BibleFieldKey;
  title: string;
  value: string;
  onChange: (value: string) => void;
  aiEnabled: boolean;
  prerequisiteWarning: string | null;
  isGenerating: boolean;
  onGenerate: () => void;
  onStopGenerate: () => void;
}

export function BibleTabContent({
  fieldKey,
  title,
  value,
  onChange,
  aiEnabled,
  prerequisiteWarning,
  isGenerating,
  onGenerate,
  onStopGenerate,
}: BibleTabContentProps) {
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [isTemplateDialogOpen, setIsTemplateDialogOpen] = useState(false);

  const charCount = value.length;
  const isEmpty = !value.trim();

  const handleInsertTemplate = () => {
    if (!isEmpty) {
      setIsTemplateDialogOpen(true);
      return;
    }
    onChange(BIBLE_TEMPLATES[fieldKey]);
  };

  const confirmInsertTemplate = () => {
    onChange(BIBLE_TEMPLATES[fieldKey]);
    setIsTemplateDialogOpen(false);
  };

  // Empty state
  if (isEmpty && !isGenerating) {
    return (
      <div className="space-y-4">
        {prerequisiteWarning && (
          <div className="rounded-md border border-yellow-500/30 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-600 dark:text-yellow-500">
            {prerequisiteWarning}
          </div>
        )}
        <div className="flex min-h-[360px] flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-border">
          <div className="text-4xl opacity-20">
            {fieldKey === "inspiration" ? "💡" : fieldKey === "world_building" ? "🌍" : fieldKey === "characters" ? "👥" : fieldKey === "outline_master" ? "📋" : fieldKey === "outline_detail" ? "📝" : "📖"}
          </div>
          <p className="text-sm text-muted-foreground">
            还没有{title}内容
          </p>
          <p className="text-xs text-muted-foreground/70">
            {aiEnabled ? "点击「AI 生成」让 AI 基于灵感创作，或点击「使用模板」手动填写" : "点击「使用模板」开始填写"}
          </p>
          <div className="flex gap-2 pt-2">
            {aiEnabled && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 border-green-600/30 text-green-600 hover:bg-green-600/10"
                onClick={onGenerate}
              >
                <Sparkles className="h-3.5 w-3.5" />
                AI 生成
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={handleInsertTemplate}
            >
              <ClipboardList className="h-3.5 w-3.5" />
              使用模板
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Prerequisite warning */}
      {prerequisiteWarning && (
        <div className="rounded-md border border-yellow-500/30 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-600 dark:text-yellow-500">
          {prerequisiteWarning}
        </div>
      )}

      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-wide text-muted-foreground">
            {title}
          </span>
          <span className="text-xs text-muted-foreground/50">· {charCount} 字</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Edit / Preview toggle */}
          <div className="flex overflow-hidden rounded-md border border-border">
            <button
              type="button"
              onClick={() => setMode("edit")}
              className={`px-3 py-1 text-xs transition-colors ${
                mode === "edit"
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              编辑
            </button>
            <button
              type="button"
              onClick={() => setMode("preview")}
              className={`px-3 py-1 text-xs transition-colors ${
                mode === "preview"
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              预览
            </button>
          </div>

          {/* Template button */}
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs"
            onClick={handleInsertTemplate}
          >
            <ClipboardList className="h-3.5 w-3.5" />
            模板
          </Button>

          {/* AI generate button */}
          {aiEnabled && (
            isGenerating ? (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs text-destructive border-destructive/30"
                onClick={onStopGenerate}
              >
                <Square className="h-3.5 w-3.5" />
                停止
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs border-green-600/30 text-green-600 hover:bg-green-600/10"
                onClick={onGenerate}
              >
                <Sparkles className="h-3.5 w-3.5" />
                AI 生成
              </Button>
            )
          )}
        </div>
      </div>

      {/* Generating indicator */}
      {isGenerating && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>AI 正在生成中... 按 Escape 或点击「停止」终止</span>
        </div>
      )}

      {/* Content area */}
      {mode === "edit" ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          readOnly={isGenerating}
          className="w-full min-h-[400px] resize-y rounded-md border border-input bg-background px-4 py-3 font-mono text-sm leading-relaxed placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      ) : (
        <div className="min-h-[400px] rounded-md border border-input bg-background px-4 py-3">
          <MarkdownPreview content={value} />
        </div>
      )}

      {/* Auto-save status */}
      <div className="text-right text-xs text-muted-foreground/50">
        已自动保存
      </div>

      <AlertDialog open={isTemplateDialogOpen} onOpenChange={setIsTemplateDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认替换内容？</AlertDialogTitle>
            <AlertDialogDescription>
              当前内容将被模板替换，该操作不可撤销。是否继续？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={confirmInsertTemplate}>继续</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
