"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Eye,
  FileText,
  Loader2,
  Sparkles,
  Square,
} from "lucide-react";
import { toast } from "sonner";

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
import { RegenerateDialog } from "@/components/regenerate-dialog";
import { api } from "@/lib/api";
import type { RegenerateOptions } from "@/lib/api-client";
import { hasStandardChapterHeadings, parseOutline, replaceVolumeChapters, type ParsedOutline } from "@/lib/outline-parser";
import { consumeTextEventStream } from "@/lib/sse";
import { BIBLE_TEMPLATES } from "@/lib/bible-templates";
import { cn } from "@/lib/utils";
import type { ProjectChapter } from "@/lib/types";

type OutlineDetailMode = "edit" | "preview" | "generate";

interface OutlineDetailTabProps {
  value: string;
  onChange: (value: string) => void;
  projectId: string;
  outlineMaster: string;
  chapters?: ProjectChapter[];
  highlightedVolumeIndex?: number | null;
}

export function OutlineDetailTab({
  value,
  onChange,
  projectId,
  outlineMaster,
  chapters = [],
  highlightedVolumeIndex = null,
}: OutlineDetailTabProps) {
  const [mode, setMode] = useState<OutlineDetailMode>("edit");
  const [generatingVolumeIndex, setGeneratingVolumeIndex] = useState<number | "all" | null>(null);
  const [expandedVolumes, setExpandedVolumes] = useState<Set<number>>(new Set());
  const [regenChaptersIndex, setRegenChaptersIndex] = useState<number | null>(null);
  const [regenVolumesOpen, setRegenVolumesOpen] = useState(false);
  const [templateConfirmOpen, setTemplateConfirmOpen] = useState(false);
  const [isRawMode, setIsRawMode] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  const parsed = useMemo(() => parseOutline(value), [value]);
  const hasVolumes = parsed.volumes.length > 0;
  const allVolumesHaveChapters = hasVolumes && parsed.volumes.every((v) => v.chapters.length > 0);
  const totalChapters = useMemo(
    () => parsed.volumes.reduce((sum, volume) => sum + volume.chapters.length, 0),
    [parsed.volumes],
  );
  const completedChapters = useMemo(
    () => new Set(chapters.filter((chapter) => chapter.word_count > 0).map((chapter) => chapter.title)),
    [chapters],
  );

  useEffect(() => {
    if (highlightedVolumeIndex === null || highlightedVolumeIndex < 0) return;
    setExpandedVolumes(new Set([highlightedVolumeIndex]));
    setMode("generate");
  }, [highlightedVolumeIndex]);

  const streamSSE = useCallback(
    async (
      fetchResponse: () => Promise<Response>,
      onChunk: (generated: string) => void,
    ) => {
      const response = await fetchResponse();
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      readerRef.current = reader;
      const generated = await consumeTextEventStream(reader, {
        onData: (_chunk, fullText) => {
          onChunk(fullText);
        },
      });

      readerRef.current = null;
      return generated;
    },
    [],
  );

  const handleStopGeneration = useCallback(() => {
    readerRef.current?.cancel();
    readerRef.current = null;
    setGeneratingVolumeIndex(null);
  }, []);

  const handleGenerateVolumes = useCallback(
    async (options?: RegenerateOptions) => {
      if (generatingVolumeIndex !== null) return;
      setGeneratingVolumeIndex("all");
      try {
        const generated = await streamSSE(
          () => api.runVolumeWorkflow(projectId, options),
          (text) => onChange(text),
        );
        if (generated) {
          await api.updateProjectBible(projectId, { outline_detail: generated });
        }
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "生成失败";
        if (message !== "The operation was cancelled.") toast.error(message);
      } finally {
        setGeneratingVolumeIndex(null);
      }
    },
    [generatingVolumeIndex, onChange, projectId, streamSSE],
  );

  const handleGenerateVolumeChapters = useCallback(
    async (volumeIndex: number, options?: RegenerateOptions) => {
      if (generatingVolumeIndex !== null) return;
      const originalValue = value;
      setGeneratingVolumeIndex(volumeIndex);
      setExpandedVolumes(new Set([volumeIndex]));
      setMode("generate");

      try {
        const generated = await streamSSE(
          () => api.runVolumeChaptersWorkflow(projectId, volumeIndex, options),
          (chaptersText) => {
            const nextValue = replaceVolumeChapters(value, volumeIndex, chaptersText);
            onChange(nextValue);
          },
        );

        if (generated) {
          if (!hasStandardChapterHeadings(generated)) {
            onChange(originalValue);
            toast.error("生成结果未包含标准章节标题（### 第 N 章：章名），已阻止写入。请重试或调整意见。");
            return;
          }
          const finalValue = replaceVolumeChapters(value, volumeIndex, generated);
          const targetVolume = parseOutline(finalValue).volumes[volumeIndex];
          if (!targetVolume || targetVolume.chapters.length === 0) {
            onChange(originalValue);
            toast.error("生成结果无法解析为章节树，已阻止写入。请重试或调整意见。");
            return;
          }
          onChange(finalValue);
          await api.updateProjectBible(projectId, { outline_detail: finalValue });
        }
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "生成失败";
        if (message !== "The operation was cancelled.") {
          onChange(originalValue);
          toast.error(message);
        }
      } finally {
        setGeneratingVolumeIndex(null);
      }
    },
    [generatingVolumeIndex, onChange, projectId, streamSSE, value],
  );

  const toggleVolume = useCallback((volumeIndex: number) => {
    setExpandedVolumes((prev) => {
      if (prev.has(volumeIndex)) return new Set();
      return new Set([volumeIndex]);
    });
  }, []);

  const handleOpenRegenerateChaptersDialog = useCallback((volumeIndex: number) => {
    setRegenChaptersIndex(volumeIndex);
  }, []);

  const handleInsertTemplate = useCallback(() => {
    if (value.trim()) {
      setTemplateConfirmOpen(true);
    } else {
      onChange(BIBLE_TEMPLATES["outline_detail"]);
      setIsRawMode(true);
    }
  }, [value, onChange]);

  const handleGenerateVolumesWithConfirm = useCallback(() => {
    if (value.trim()) {
      setRegenVolumesOpen(true);
    } else {
      handleGenerateVolumes();
    }
  }, [value, handleGenerateVolumes]);

  const handleRerunVolumeWorkflowConfirm = useCallback(
    (feedback: string) => {
      setRegenVolumesOpen(false);
      handleGenerateVolumes({
        previousOutput: value || undefined,
        userFeedback: feedback || undefined,
      });
    },
    [handleGenerateVolumes, value],
  );

  const handleRegenerateChaptersConfirm = useCallback(
    (feedback: string) => {
      const index = regenChaptersIndex;
      if (index === null) return;
      setRegenChaptersIndex(null);
      handleGenerateVolumeChapters(index, {
        previousOutput: value || undefined,
        userFeedback: feedback || undefined,
      });
    },
    [regenChaptersIndex, handleGenerateVolumeChapters, value],
  );

  const toolbar = (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">
          分卷与章节细纲
        </span>
        <span className="text-xs text-muted-foreground/50">
          · {parsed.volumes.length} 卷 · {totalChapters} 章
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex overflow-hidden rounded-md border border-border">
          <button
            type="button"
            onClick={() => setMode("edit")}
            className={`px-3 py-1 text-xs transition-colors ${
              mode !== "preview"
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

        <Button variant="outline" size="sm" className="gap-1.5 text-xs" onClick={handleInsertTemplate}>
          <ClipboardList className="h-3.5 w-3.5" />
          模板
        </Button>

        {generatingVolumeIndex !== null ? (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs text-destructive border-destructive/30"
            onClick={handleStopGeneration}
          >
            <Square className="h-3.5 w-3.5" />
            停止
          </Button>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs border-green-600/30 text-green-600 hover:bg-green-600/10"
            onClick={handleGenerateVolumesWithConfirm}
          >
            <Sparkles className="h-3.5 w-3.5" />
            AI 生成
          </Button>
        )}

        <Button variant="ghost" size="sm" className="gap-1.5 text-xs" onClick={() => setIsRawMode((r) => !r)}>
          {isRawMode ? <Eye className="h-3.5 w-3.5" /> : <FileText className="h-3.5 w-3.5" />}
          {isRawMode ? "返回结构化视图" : "编辑原始 Markdown"}
        </Button>
      </div>
    </div>
  );

  if (isRawMode) {
    return (
      <div className="space-y-4">
        {toolbar}
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full min-h-[400px] resize-y rounded-md border border-input bg-background px-4 py-3 text-sm font-mono leading-relaxed placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder="使用 Markdown 格式编辑分卷与章节细纲..."
        />
      </div>
    );
  }

  if (!hasVolumes) {
    return (
      <div className="space-y-4">
        {toolbar}
        <EmptyVolumesState
          outlineMaster={outlineMaster}
          isGenerating={generatingVolumeIndex === "all"}
          onGenerateVolumes={handleGenerateVolumesWithConfirm}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {toolbar}

      {generatingVolumeIndex !== null && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>
            {generatingVolumeIndex === "all"
              ? "AI 正在生成分卷结构..."
              : `AI 正在为第 ${generatingVolumeIndex + 1} 卷生成章节细纲...`}
          </span>
        </div>
      )}

      {mode === "preview" ? (
        <div className="min-h-[400px] rounded-md border border-input bg-background px-4 py-3">
          <MarkdownPreview content={value} />
        </div>
      ) : (
        <div className="space-y-4">
          {parsed.volumes.map((vol, vi) => (
            <VolumeCard
              key={`${vol.title}-${vi}`}
              outline={parsed}
              value={value}
              projectId={projectId}
              volume={vol}
              volumeIndex={vi}
              isExpanded={expandedVolumes.has(vi)}
              isGenerating={generatingVolumeIndex === vi}
              completedChapters={completedChapters}
              highlighted={highlightedVolumeIndex === vi}
              onToggleExpand={() => toggleVolume(vi)}
              onGenerate={() => handleGenerateVolumeChapters(vi)}
              onRegenerate={() => handleOpenRegenerateChaptersDialog(vi)}
            />
          ))}
        </div>
      )}

      {allVolumesHaveChapters && (
        <p className="text-xs text-center text-emerald-500">
          ✓ 所有分卷章节已生成完毕，可以进入编辑器开始写作
        </p>
      )}

      <RegenerateDialog
        open={regenChaptersIndex !== null}
        title={
          regenChaptersIndex !== null
            ? `重新生成第 ${regenChaptersIndex + 1} 卷章节细纲`
            : ""
        }
        description="当前卷下已生成的章节细纲将被覆盖。你可以填写意见指导生成方向（可选）。"
        busy={generatingVolumeIndex !== null}
        onCancel={() => setRegenChaptersIndex(null)}
        onConfirm={handleRegenerateChaptersConfirm}
      />

      <RegenerateDialog
        open={regenVolumesOpen}
        title="重新生成分卷结构"
        description="当前已有分卷/章节细纲，将基于现有结构重写。你可以填写意见指导生成方向（可选）。"
        busy={generatingVolumeIndex !== null}
        onCancel={() => setRegenVolumesOpen(false)}
        onConfirm={handleRerunVolumeWorkflowConfirm}
      />

      <AlertDialog open={templateConfirmOpen} onOpenChange={(open) => !open && setTemplateConfirmOpen(false)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认插入模板？</AlertDialogTitle>
            <AlertDialogDescription>
              当前已有内容，插入模板将覆盖现有内容。该操作不可撤销。是否继续？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                onChange(BIBLE_TEMPLATES["outline_detail"]);
                setIsRawMode(true);
                setTemplateConfirmOpen(false);
              }}
            >
              继续
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function EmptyVolumesState({
  outlineMaster,
  isGenerating,
  onGenerateVolumes,
}: {
  outlineMaster: string;
  isGenerating: boolean;
  onGenerateVolumes: () => void;
}) {
  return (
    <div className="space-y-4">
      {!outlineMaster.trim() && (
        <div className="rounded-md border border-yellow-500/30 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-600">
          💡 建议先完善「总纲」后再生成分卷结构，AI 会参考这些内容来规划分卷。
        </div>
      )}
      <div className="flex min-h-[360px] flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-border">
        <div className="text-4xl opacity-20">📝</div>
        <p className="text-sm text-muted-foreground">还没有分卷结构</p>
        <p className="text-xs text-muted-foreground/70">
          点击「AI 生成」创建分卷结构，再按卷补齐章节细纲
        </p>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 border-green-600/30 text-green-600 hover:bg-green-600/10"
          disabled={isGenerating}
          onClick={onGenerateVolumes}
        >
          {isGenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          {isGenerating ? "生成中..." : "AI 生成"}
        </Button>
      </div>
    </div>
  );
}

function VolumeCard({
  outline,
  value,
  projectId,
  volume,
  volumeIndex,
  isExpanded,
  isGenerating,
  completedChapters,
  highlighted,
  onToggleExpand,
  onGenerate,
  onRegenerate,
}: {
  outline: ParsedOutline;
  value: string;
  projectId: string;
  volume: ParsedOutline["volumes"][number];
  volumeIndex: number;
  isExpanded: boolean;
  isGenerating: boolean;
  completedChapters: Set<string>;
  highlighted: boolean;
  onToggleExpand: () => void;
  onGenerate: () => void;
  onRegenerate: () => void;
}) {
  const [isBodyExpanded, setIsBodyExpanded] = useState(false);
  const chapterCount = volume.chapters.length;
  const completedCount = volume.chapters.filter((chapter) => completedChapters.has(chapter.title)).length;
  const volumeTitle = getVolumeTitle(volume.title);
  const bodyPreviewMarkdown = getVolumeBodyPreviewMarkdown(volume.bodyMarkdown, volume.meta);

  return (
    <div
      className={cn(
        "rounded-md border bg-card transition-colors",
        highlighted ? "border-primary ring-2 ring-primary/10" : "border-border",
      )}
      data-volume-index={volumeIndex}
    >
      <div className="flex flex-col gap-3 p-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            <span>第 {volumeIndex + 1} 卷</span>
            <span className="text-muted-foreground/40">·</span>
            <span>{chapterCount} 章</span>
            <span className="text-muted-foreground/40">·</span>
            <span className="text-emerald-600">已完成 {completedCount}/{chapterCount} 章</span>
            {!chapterCount ? (
              <>
                <span className="text-muted-foreground/40">·</span>
                <span className="text-amber-600">尚未生成章节细纲</span>
              </>
            ) : null}
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-semibold leading-6">{volumeTitle}</h4>
            {volume.meta ? (
              <p className="max-w-3xl text-xs leading-5 text-muted-foreground">{volume.meta}</p>
            ) : (
              <p className="text-xs text-muted-foreground">暂无卷简介</p>
            )}
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {bodyPreviewMarkdown ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="gap-1.5 text-xs text-muted-foreground"
              onClick={() => setIsBodyExpanded((prev) => !prev)}
            >
              {isBodyExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              {isBodyExpanded ? "收起卷级内容" : "展开卷级内容"}
            </Button>
          ) : null}
          {!chapterCount ? (
            <Button size="sm" className="gap-2" disabled={isGenerating} onClick={onGenerate}>
              {isGenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              {isGenerating ? "生成中..." : "生成本卷章节细纲"}
            </Button>
          ) : (
            <>
              <Button type="button" variant="outline" size="sm" onClick={onToggleExpand}>
                {isExpanded ? "收起章节" : "查看章节"}
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={onRegenerate}>
                重新生成章节细纲
              </Button>
            </>
          )}
        </div>
      </div>

      {isBodyExpanded && bodyPreviewMarkdown ? (
        <div className="border-t border-border px-4 py-3">
          <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
            卷级细纲
          </div>
          <MarkdownPreview content={bodyPreviewMarkdown} className="text-xs" />
        </div>
      ) : null}

      {isExpanded && chapterCount > 0 ? (
        <VolumeChapterList
          outline={outline}
          chapters={volume.chapters}
          projectId={projectId}
          volumeIndex={volumeIndex}
        />
      ) : null}
      {isExpanded && chapterCount === 0 && value.trim() ? (
        <p className="border-t border-border px-4 py-3 text-xs text-muted-foreground">本卷暂未生成章节细纲。</p>
      ) : null}
    </div>
  );
}

function VolumeChapterList({
  outline,
  chapters,
  projectId,
  volumeIndex,
}: {
  outline: ParsedOutline;
  chapters: ParsedOutline["volumes"][number]["chapters"];
  projectId: string;
  volumeIndex: number;
}) {
  return (
    <div className="border-t border-border">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-2">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
          章节树
        </p>
        <p className="text-xs text-muted-foreground/60">{chapters.length} 章</p>
      </div>
      {chapters.map((chapter, chapterIndex) => (
        <div
          key={`${chapter.title}-${chapterIndex}`}
          className="group border-b border-border px-4 py-3 last:border-b-0 hover:bg-muted/40"
        >
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1 space-y-2">
              <Link
                href={buildEditorHref(projectId, volumeIndex, chapterIndex, "navigate")}
                className="block min-w-0 text-sm font-medium text-foreground transition-colors hover:underline"
              >
                {chapter.title}
              </Link>
              <div className="space-y-1 text-xs leading-5 text-muted-foreground">
                {chapter.coreEvent && (
                  <p>
                    <span className="font-medium text-foreground/70">核心事件：</span>
                    {chapter.coreEvent}
                  </p>
                )}
                {chapter.chapterHook && (
                  <p>
                    <span className="font-medium text-foreground/70">章末钩子：</span>
                    {chapter.chapterHook}
                  </p>
                )}
              </div>
            </div>
            <Button variant="secondary" size="sm" asChild>
              <Link
                href={buildEditorHref(projectId, volumeIndex, chapterIndex, "generate_beats")}
                aria-label={`AI 生成 ${chapter.title}`}
              >
                生成节拍
              </Link>
            </Button>
          </div>
        </div>
      ))}
      {outline.parseErrors.length > 0 && (
        <p className="border-t border-border px-4 py-3 text-xs text-amber-600">
          当前结构包含无法解析的 Markdown 片段，建议通过原始 Markdown 检查。
        </p>
      )}
    </div>
  );
}

function getVolumeTitle(title: string) {
  return title.trim() || "未分卷章节";
}

function getVolumeBodyPreviewMarkdown(bodyMarkdown: string, meta: string) {
  if (!bodyMarkdown.trim()) return "";
  const lines = bodyMarkdown.split("\n");
  const firstContentLine = lines.findIndex((line) => line.trim());
  if (firstContentLine !== -1) {
    const firstLine = lines[firstContentLine].trim();
    if (firstLine === `> ${meta}` || firstLine.replace(/^>\s*/, "") === meta) {
      lines.splice(firstContentLine, 1);
    }
  }
  return lines.join("\n").trim();
}

function buildEditorHref(
  projectId: string,
  volumeIndex: number,
  chapterIndex: number,
  intent: "navigate" | "generate_beats",
) {
  return `/projects/${projectId}/editor?volumeIndex=${volumeIndex}&chapterIndex=${chapterIndex}&intent=${intent}`;
}
