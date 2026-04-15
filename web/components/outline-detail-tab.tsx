"use client";

import { useCallback, useRef, useState } from "react";
import { BookOpen, ChevronDown, ChevronRight, FileText, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { parseOutline } from "@/lib/outline-parser";

interface OutlineDetailTabProps {
  value: string;
  onChange: (value: string) => void;
  projectId: string;
  outlineMaster: string;
}

export function OutlineDetailTab({
  value,
  onChange,
  projectId,
  outlineMaster,
}: OutlineDetailTabProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatingVolumeIndex, setGeneratingVolumeIndex] = useState<number | null>(null);
  const [isRawMode, setIsRawMode] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  const parsed = parseOutline(value);
  const hasVolumes = parsed.volumes.length > 0;
  const allVolumesHaveChapters = hasVolumes && parsed.volumes.every((v) => v.chapters.length > 0);

  const streamSSE = useCallback(
    async (
      fetchResponse: () => Promise<Response>,
      onChunk: (generated: string) => void,
    ) => {
      const response = await fetchResponse();
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();
      let buffer = "";
      let generated = "";
      let sseError = false;

      while (true) {
        const { done, value: chunk } = await reader.read();
        if (done) break;

        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: error")) {
            sseError = true;
          } else if (line.startsWith("data: ")) {
            const dataStr = line.substring(6);
            if (!dataStr) continue;
            if (sseError) {
              const detail = (() => {
                try { return JSON.parse(dataStr); } catch { return dataStr; }
              })();
              throw new Error(detail || "生成过程中发生错误");
            }
            try {
              const parsed = JSON.parse(dataStr);
              generated += parsed;
              onChunk(generated);
            } catch {
              // ignore parse errors
            }
          }
        }
      }
      readerRef.current = null;
      return generated;
    },
    [],
  );

  const handleGenerateVolumes = useCallback(async () => {
    if (isGenerating) return;
    setIsGenerating(true);
    try {
      const generated = await streamSSE(
        () => api.generateVolumes(projectId),
        (text) => onChange(text),
      );
      if (generated) {
        await api.updateProject(projectId, { outline_detail: generated });
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "生成失败";
      if (message !== "The operation was cancelled.") toast.error(message);
    } finally {
      setIsGenerating(false);
    }
  }, [isGenerating, projectId, onChange, streamSSE]);

  const handleGenerateVolumeChapters = useCallback(
    async (volumeIndex: number) => {
      if (generatingVolumeIndex !== null) return;
      setGeneratingVolumeIndex(volumeIndex);
      try {
        const generated = await streamSSE(
          () => api.generateVolumeChapters(projectId, volumeIndex),
          (chaptersText) => {
            // Insert chapters into the correct volume position
            const volumeStarts: number[] = [];
            const regex = /^## /gm;
            let match;
            while ((match = regex.exec(value)) !== null) {
              volumeStarts.push(match.index);
            }

            let insertPos: number;
            if (volumeIndex + 1 < volumeStarts.length) {
              insertPos = volumeStarts[volumeIndex + 1];
            } else {
              insertPos = value.length;
            }

            const before = value.substring(0, insertPos).trimEnd();
            const after = value.substring(insertPos);
            onChange(before + "\n\n" + chaptersText.trim() + "\n\n" + after);
          },
        );
        if (generated) {
          // Compute final value and save
          const volumeStarts: number[] = [];
          const regex = /^## /gm;
          let match;
          while ((match = regex.exec(value)) !== null) {
            volumeStarts.push(match.index);
          }
          let insertPos: number;
          if (volumeIndex + 1 < volumeStarts.length) {
            insertPos = volumeStarts[volumeIndex + 1];
          } else {
            insertPos = value.length;
          }
          const before = value.substring(0, insertPos).trimEnd();
          const after = value.substring(insertPos);
          const finalValue = before + "\n\n" + generated.trim() + "\n\n" + after;
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
    [generatingVolumeIndex, projectId, value, onChange, streamSSE],
  );

  // Raw Markdown editor mode
  if (isRawMode) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">分卷与章节细纲</h3>
          <Button variant="outline" size="sm" onClick={() => setIsRawMode(false)}>
            返回结构化视图
          </Button>
        </div>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full min-h-[400px] resize-y rounded-md border border-input bg-background px-3 py-2 text-sm font-mono leading-relaxed placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder="使用 Markdown 格式编辑分卷与章节细纲..."
        />
      </div>
    );
  }

  // State 1: Empty
  if (!hasVolumes) {
    return (
      <div className="space-y-4">
        <div className="flex flex-col items-center gap-4 py-12">
          <BookOpen className="h-10 w-10 text-muted-foreground/30" />
          <div className="text-center space-y-1">
            <p className="text-sm font-medium">分卷与章节细纲</p>
            <p className="text-xs text-muted-foreground">
              先生成分卷结构，再逐卷展开章节细纲
            </p>
          </div>
          {!outlineMaster.trim() && (
            <p className="text-xs text-amber-500">
              💡 建议先完善「总纲」后再生成分卷结构
            </p>
          )}
          <Button
            onClick={handleGenerateVolumes}
            disabled={isGenerating}
            className="gap-2"
          >
            {isGenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isGenerating ? "生成中..." : "生成分卷结构"}
          </Button>
        </div>
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" className="gap-1.5 text-xs" onClick={() => setIsRawMode(true)}>
            <FileText className="h-3.5 w-3.5" />
            编辑原始 Markdown
          </Button>
        </div>
      </div>
    );
  }

  // State 2 & 3: Volumes exist
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">
          分卷与章节细纲
          <span className="ml-2 text-xs text-muted-foreground font-normal">
            {parsed.volumes.length} 卷
          </span>
        </h3>
        <Button variant="ghost" size="sm" className="gap-1.5 text-xs" onClick={() => setIsRawMode(true)}>
          <FileText className="h-3.5 w-3.5" />
          编辑原始 Markdown
        </Button>
      </div>

      <div className="space-y-3">
        {parsed.volumes.map((vol, vi) => {
          const hasChapters = vol.chapters.length > 0;
          const isGeneratingThis = generatingVolumeIndex === vi;

          return (
            <div key={vi} className="rounded-lg border border-border p-4 space-y-3">
              <div>
                <h4 className="text-sm font-medium">{vol.title}</h4>
                {vol.meta && (
                  <p className="text-xs text-muted-foreground mt-0.5">{vol.meta}</p>
                )}
              </div>

              {hasChapters ? (
                <VolumeChapterList chapters={vol.chapters} />
              ) : (
                <Button
                  size="sm"
                  variant="secondary"
                  className="gap-2 w-full"
                  onClick={() => handleGenerateVolumeChapters(vi)}
                  disabled={generatingVolumeIndex !== null}
                >
                  {isGeneratingThis ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  {isGeneratingThis ? "生成中..." : "生成本卷章节"}
                </Button>
              )}
            </div>
          );
        })}
      </div>

      {allVolumesHaveChapters && (
        <p className="text-xs text-center text-emerald-500">
          ✓ 所有分卷章节已生成完毕，可以进入编辑器开始写作
        </p>
      )}
    </div>
  );
}

function VolumeChapterList({ chapters }: { chapters: ReturnType<typeof parseOutline>["volumes"][0]["chapters"] }) {
  const [expanded, setExpanded] = useState(false);
  const displayChapters = expanded ? chapters : chapters.slice(0, 3);

  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground">{chapters.length} 章</p>
      {displayChapters.map((ch, ci) => (
        <div key={ci} className="text-xs text-muted-foreground pl-2 border-l border-border">
          {ch.title}
        </div>
      ))}
      {chapters.length > 3 && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-primary hover:underline"
        >
          {expanded ? "收起" : `查看全部 ${chapters.length} 章`}
        </button>
      )}
    </div>
  );
}
