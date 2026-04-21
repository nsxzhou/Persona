"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ClipboardList, FileText, Loader2, Sparkles, Square } from "lucide-react";
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
import { parseOutline, type ParsedOutline } from "@/lib/outline-parser";
import { consumeTextEventStream } from "@/lib/sse";
import { BIBLE_TEMPLATES } from "@/lib/bible-templates";
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
          () => api.generateVolumes(projectId, options),
          (text) => onChange(text),
        );
        if (generated) {
          await api.updateProject(projectId, { outline_detail: generated });
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
      setGeneratingVolumeIndex(volumeIndex);
      setExpandedVolumes(new Set([volumeIndex]));
      setMode("generate");

      try {
        const generated = await streamSSE(
          () => api.generateVolumeChapters(projectId, volumeIndex, options),
          (chaptersText) => {
            const nextValue = replaceVolumeChapters(value, volumeIndex, chaptersText);
            onChange(nextValue);
          },
        );

        if (generated) {
          const finalValue = replaceVolumeChapters(value, volumeIndex, generated);
          onChange(finalValue);
          await api.updateProject(projectId, { outline_detail: finalValue });
        }
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "生成失败";
        if (message !== "The operation was cancelled.") toast.error(message);
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

  const handleRegenerateVolumesConfirm = useCallback(
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
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">分卷与章节细纲</span>
        <span className="text-xs text-muted-foreground/50">· {parsed.volumes.length} 卷</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex overflow-hidden rounded-md border border-border">
          <button
            type="button"
            onClick={() => setMode("edit")}
            className={`px-3 py-1 text-xs transition-colors ${
              mode === "edit" ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            编辑
          </button>
          <button
            type="button"
            onClick={() => setMode("preview")}
            className={`px-3 py-1 text-xs transition-colors ${
              mode === "preview" ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground"
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

        <Button variant="ghost" size="sm" className="gap-1.5 text-xs" onClick={() => setIsRawMode(true)}>
          <FileText className="h-3.5 w-3.5" />
          编辑原始 Markdown
        </Button>
      </div>
    </div>
  );

  if (isRawMode) {
    return (
      <div className="space-y-3">
        {toolbar}
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">原始 Markdown 适合手动修正与兜底编辑。</p>
          <Button variant="outline" size="sm" onClick={() => setIsRawMode(false)}>
            返回结构化视图
          </Button>
        </div>
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
      <div className="space-y-3">
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
    <div className="space-y-3">
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
        <div className="rounded-lg border border-input bg-background px-4 py-3">
          <MarkdownPreview content={value} />
        </div>
      ) : (
        <div className="space-y-3">
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
        onConfirm={handleRegenerateVolumesConfirm}
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
  const chapterCount = volume.chapters.length;
  const completedCount = volume.chapters.filter((chapter) => completedChapters.has(chapter.title)).length;
  const volumeTitle = getVolumeTitle(volume.title);

  return (
    <div
      className={`rounded-xl border bg-card p-4 shadow-sm transition-colors ${
        highlighted ? "border-primary ring-2 ring-primary/15" : "border-border"
      }`}
      data-volume-index={volumeIndex}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-2">
          <div className="space-y-1">
            <h4 className="text-sm font-semibold">{volumeTitle}</h4>
            {volume.meta ? (
              <p className="text-xs text-muted-foreground leading-5">{volume.meta}</p>
            ) : (
              <p className="text-xs text-muted-foreground">暂无卷简介</p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
            <span className="rounded-full bg-muted px-2.5 py-1">{chapterCount} 章</span>
            <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-emerald-600">
              已完成 {completedCount}/{chapterCount} 章
            </span>
            {!chapterCount && (
              <span className="rounded-full bg-amber-500/10 px-2.5 py-1 text-amber-600">
                尚未生成章节细纲
              </span>
            )}
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
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

      {isExpanded && chapterCount > 0 ? (
        <VolumeChapterList
          outline={outline}
          value={value}
          chapters={volume.chapters}
          projectId={projectId}
          volumeIndex={volumeIndex}
        />
      ) : null}
    </div>
  );
}

function VolumeChapterList({
  outline,
  value,
  chapters,
  projectId,
  volumeIndex,
}: {
  outline: ParsedOutline;
  value: string;
  chapters: ParsedOutline["volumes"][number]["chapters"];
  projectId: string;
  volumeIndex: number;
}) {
  return (
    <div className="mt-4 space-y-2 border-t border-border pt-4">
      {chapters.map((chapter, chapterIndex) => (
        <div
          key={`${chapter.title}-${chapterIndex}`}
          className="flex items-center gap-3 rounded-lg border border-border/70 bg-background px-3 py-2"
        >
          <Link
            href={buildEditorHref(projectId, volumeIndex, chapterIndex, "navigate")}
            className="min-w-0 flex-1 text-sm text-foreground transition-colors hover:text-primary hover:underline"
          >
            {chapter.title}
          </Link>
          <Button variant="secondary" size="sm" asChild>
            <Link
              href={buildEditorHref(projectId, volumeIndex, chapterIndex, "generate_beats")}
              aria-label={`AI 生成 ${chapter.title}`}
            >
              生成节拍
            </Link>
          </Button>
        </div>
      ))}
      {outline.parseErrors.length > 0 && (
        <p className="text-xs text-amber-600">
          当前结构包含无法解析的 Markdown 片段，建议通过原始 Markdown 检查。
        </p>
      )}
      {!chapters.length && value.trim() && (
        <p className="text-xs text-muted-foreground">本卷暂未生成章节细纲。</p>
      )}
    </div>
  );
}

function getVolumeTitle(title: string) {
  return title.trim() || "未分卷章节";
}

function buildEditorHref(
  projectId: string,
  volumeIndex: number,
  chapterIndex: number,
  intent: "navigate" | "generate_beats",
) {
  return `/projects/${projectId}/editor?volumeIndex=${volumeIndex}&chapterIndex=${chapterIndex}&intent=${intent}`;
}

function replaceVolumeChapters(value: string, volumeIndex: number, generatedChapters: string) {
  const parsed = parseOutline(value);
  const target = parsed.volumes[volumeIndex];
  if (!target) return value;

  const lines: string[] = [];

  parsed.volumes.forEach((volume, index) => {
    lines.push(`## ${volume.title}`);
    if (volume.meta) lines.push(`> ${volume.meta}`);
    lines.push("");

    if (index === volumeIndex) {
      const normalized = generatedChapters.trim();
      if (normalized) {
        lines.push(normalized);
        lines.push("");
      }
      return;
    }

    if (volume.chapters.length > 0) {
      volume.chapters.forEach((chapter) => {
        lines.push(chapter.rawMarkdown);
        lines.push("");
      });
    }
  });

  return lines.join("\n").trim();
}
