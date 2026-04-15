"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Project } from "@/lib/types";
import { api } from "@/lib/api";
import { ArrowLeft, BookOpen, ListOrdered, Loader2, Sparkles, Square } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { EditorSidePanel } from "@/components/editor-side-panel";
import { BibleDiffDialog } from "@/components/bible-diff-dialog";
import { BeatPanel } from "@/components/beat-panel";

export function ZenEditorView({
  project,
  activeProfileName,
}: {
  project: Project;
  activeProfileName?: string;
}) {
  const [content, setContent] = useState(project.content || "");
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const rafRef = useRef<number | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [bibleDiff, setBibleDiff] = useState<{
    open: boolean;
    current: string;
    proposed: string;
  }>({ open: false, current: "", proposed: "" });

  // Mutable project data for bible fields (so side panel reflects updates)
  const [projectData, setProjectData] = useState(project);

  // ---- Beat mode ----
  const [isBeatPanelOpen, setIsBeatPanelOpen] = useState(false);
  const [beats, setBeats] = useState<string[]>([]);
  const [currentBeatIndex, setCurrentBeatIndex] = useState(-1);
  const [isGeneratingBeats, setIsGeneratingBeats] = useState(false);
  const [isExpandingBeat, setIsExpandingBeat] = useState(false);

  const handleGenerateBeats = async () => {
    if (isGeneratingBeats) return;
    setIsGeneratingBeats(true);
    try {
      const textarea = textareaRef.current;
      const textBeforeCursor = textarea
        ? content.substring(0, textarea.selectionStart)
        : content;

      const res = await fetch(
        `/api/v1/projects/${project.id}/editor/generate-beats`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text_before_cursor: textBeforeCursor,
            story_bible: project.story_bible ?? "",
            outline_detail: project.outline_detail ?? "",
          }),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "生成节拍失败");
      }
      const data = await res.json();
      setBeats(data.beats);
      setCurrentBeatIndex(-1);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "生成节拍失败");
    } finally {
      setIsGeneratingBeats(false);
    }
  };

  const handleStartBeatExpand = async () => {
    if (beats.length === 0 || isExpandingBeat || isGenerating) return;

    // Capture cursor position once before the loop to avoid stale content/DOM mismatch
    const textarea = textareaRef.current;
    const cursorPos = textarea ? textarea.selectionStart : content.length;
    const textBeforeCursor = content.substring(0, cursorPos);
    const textAfterCursor = content.substring(cursorPos);

    let beatsProse = "";
    for (let i = 0; i < beats.length; i++) {
      setCurrentBeatIndex(i);
      setIsExpandingBeat(true);

      try {

        const response = await fetch(
          `/api/v1/projects/${project.id}/editor/expand-beat`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              text_before_cursor: textBeforeCursor,
              story_bible: project.story_bible ?? "",
              outline_detail: project.outline_detail ?? "",
              beat: beats[i],
              beat_index: i,
              total_beats: beats.length,
              preceding_beats_prose: beatsProse,
            }),
          },
        );

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || "展开节拍失败");
        }
        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        readerRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = "";
        let beatGenerated = "";
        let sseError = false;
        let needsFlush = false;

        const flushToState = () => {
          rafRef.current = null;
          const newContent = textBeforeCursor + beatsProse + beatGenerated + textAfterCursor;
          setContent(newContent);
          needsFlush = false;
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: error")) {
              sseError = true;
            } else if (line.startsWith("data: ")) {
              const dataStr = line.substring(6);
              if (!dataStr) continue;
              if (sseError) {
                const detail = (() => { try { return JSON.parse(dataStr); } catch { return dataStr; } })();
                throw new Error(detail || "展开过程中发生错误");
              }
              try {
                const parsed = JSON.parse(dataStr);
                beatGenerated += parsed;
                needsFlush = true;
              } catch {
                // ignore
              }
            }
          }
          if (needsFlush && rafRef.current === null) {
            rafRef.current = requestAnimationFrame(flushToState);
          }
        }
        // Final flush after stream ends
        if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
        flushToState();

        beatsProse += beatGenerated;
        readerRef.current = null;
      } catch (e: unknown) {
        readerRef.current = null;
        const message = e instanceof Error ? e.message : "展开失败";
        if (message !== "The operation was cancelled.") {
          toast.error(message);
        }
        break;
      }
    }
    setIsExpandingBeat(false);
    setCurrentBeatIndex(-1);
  };

  // 防抖保存（流式生成期间跳过，生成结束后由 handler 显式保存）
  useEffect(() => {
    if (isGenerating || isExpandingBeat) return;
    if (content === project.content) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      setIsSaving(true);
      try {
        await api.updateProject(project.id, { content });
      } catch (e) {
        console.error("Failed to save content", e);
        toast.error("自动保存失败");
      } finally {
        setIsSaving(false);
      }
    }, 1000);

    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    };
  }, [content, project.id, project.content, isGenerating, isExpandingBeat]);

  // 停止生成
  const handleStop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    readerRef.current?.cancel();
    readerRef.current = null;
    setIsGenerating(false);
  }, []);

  // 触发续写
  const handleGenerate = async () => {
    if (!project.style_profile_id) {
      toast.error("项目未挂载风格档案，无法进行续写。请先在项目设置中选择风格档案。");
      return;
    }
    if (isGenerating || isExpandingBeat) return;

    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPosition = textarea.selectionStart;
    const textBeforeCursor = content.substring(0, cursorPosition);

    setIsGenerating(true);

    try {
      const response = await fetch(`/api/v1/projects/${project.id}/editor/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text_before_cursor: textBeforeCursor }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "请求失败");
      }

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();
      let buffer = "";

      let currentGenerated = "";
      let sseError = false;
      let needsFlush = false;

      const flushToState = () => {
        rafRef.current = null;
        const captured = currentGenerated;
        setContent((prev) => {
          const before = textBeforeCursor;
          const after = prev.substring(cursorPosition);
          return before + captured + after;
        });
        needsFlush = false;
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: error")) {
            sseError = true;
          } else if (line.startsWith("data: ")) {
            const dataStr = line.substring(6);
            if (!dataStr) continue;
            if (sseError) {
              const detail = (() => { try { return JSON.parse(dataStr); } catch { return dataStr; } })();
              throw new Error(detail || "生成过程中发生错误");
            }
            try {
              const parsed = JSON.parse(dataStr);
              currentGenerated += parsed;
              needsFlush = true;
            } catch (e) {
              console.error("Failed to parse SSE data:", dataStr);
            }
          }
        }
        if (needsFlush && rafRef.current === null) {
          rafRef.current = requestAnimationFrame(flushToState);
        }
      }
      // Final flush after stream ends
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      flushToState();

      // Let the cursor move to the end of the newly generated text
      requestAnimationFrame(() => {
        if (textarea) {
          const newPos = cursorPosition + currentGenerated.length;
          textarea.setSelectionRange(newPos, newPos);
          textarea.focus();
        }
      });

      // 续写完成后，尝试提议故事圣经更新（仅当生成内容足够长时触发，避免短续写浪费 token）
      const MIN_LENGTH_FOR_BIBLE_UPDATE = 200;
      if (currentGenerated.trim().length >= MIN_LENGTH_FOR_BIBLE_UPDATE && projectData.story_bible !== undefined) {
        try {
          const bibleRes = await fetch(
            `/api/v1/projects/${project.id}/editor/propose-bible-update`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                current_bible: projectData.story_bible,
                new_content_context: currentGenerated,
              }),
            },
          );
          if (bibleRes.ok) {
            const { proposed_bible } = await bibleRes.json();
            if (proposed_bible && proposed_bible !== projectData.story_bible) {
              setBibleDiff({
                open: true,
                current: projectData.story_bible,
                proposed: proposed_bible,
              });
            }
          }
        } catch {
          // 圣经更新提议失败不阻塞主流程
        }
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "续写失败";
      if (message !== "The operation was cancelled.") {
        toast.error(message || "续写失败，请稍后重试");
      }
    } finally {
      readerRef.current = null;
      setIsGenerating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape" && isGenerating) {
      e.preventDefault();
      handleStop();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "b") {
      e.preventDefault();
      setIsPanelOpen((prev) => !prev);
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "j") {
      e.preventDefault();
      setIsBeatPanelOpen((prev) => !prev);
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "j") {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <div className="flex flex-col h-screen w-full bg-background text-foreground">
      {/* 顶部导航 */}
      <header className="flex items-center justify-between px-6 py-4 border-b shrink-0">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href={`/projects/${project.id}`}>
              <ArrowLeft className="w-5 h-5" />
            </Link>
          </Button>
          <h1 className="text-lg font-medium">{project.name}</h1>
        </div>

        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>保存中...</span>
              </>
            ) : (
              <span>已保存</span>
            )}
          </div>
          <div className="flex items-center gap-2 bg-muted/50 px-3 py-1.5 rounded-md">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="font-medium">
              {activeProfileName ? activeProfileName : "未挂载风格"}
            </span>
          </div>
          <Button
            variant={isPanelOpen ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setIsPanelOpen((prev) => !prev)}
            className="gap-1.5"
            title="设定面板 (Cmd+B)"
          >
            <BookOpen className="w-4 h-4" />
          </Button>
          <Button
            variant={isBeatPanelOpen ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setIsBeatPanelOpen((prev) => !prev)}
            className="gap-1.5"
            title="节拍写作"
          >
            <ListOrdered className="w-4 h-4" />
          </Button>
          {isGenerating ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleStop}
              className="gap-2 text-destructive border-destructive/50 hover:bg-destructive/10"
            >
              <Square className="w-4 h-4" />
              停止 (Esc)
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerate}
              disabled={!project.style_profile_id}
              className="gap-2"
            >
              <Sparkles className="w-4 h-4" />
              AI 续写 (Cmd+J)
            </Button>
          )}
        </div>
      </header>

      {/* 编辑区 + 侧面板 */}
      <main className="flex-1 overflow-hidden flex bg-muted/20">
        <div className="flex-1 flex justify-center overflow-hidden">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="开始创作... (按 Cmd+J 进行 AI 续写)"
            className="w-full max-w-4xl h-full p-8 md:p-12 resize-none bg-transparent outline-none text-lg leading-relaxed shadow-none border-none focus:ring-0 text-foreground/90 placeholder:text-muted-foreground/50"
            style={{
              fontFamily: "var(--font-serif), serif",
            }}
          />
        </div>
        {isPanelOpen && (
          <EditorSidePanel
            project={projectData}
            onClose={() => setIsPanelOpen(false)}
            onFieldChange={(field, value) => setProjectData((prev) => ({ ...prev, [field]: value }))}
          />
        )}
        {isBeatPanelOpen && (
          <BeatPanel
            beats={beats}
            currentBeatIndex={currentBeatIndex}
            isExpandingBeat={isExpandingBeat}
            isGeneratingBeats={isGeneratingBeats}
            onGenerateBeats={handleGenerateBeats}
            onBeatsChange={setBeats}
            onStartExpand={handleStartBeatExpand}
            onClose={() => setIsBeatPanelOpen(false)}
          />
        )}
      </main>

      {/* 故事圣经更新提议对话框 */}
      <BibleDiffDialog
        open={bibleDiff.open}
        currentBible={bibleDiff.current}
        proposedBible={bibleDiff.proposed}
        onAccept={async (bible) => {
          try {
            await api.updateProject(project.id, { story_bible: bible });
            setProjectData((prev) => ({ ...prev, story_bible: bible }));
            toast.success("故事圣经已更新");
          } catch {
            toast.error("更新故事圣经失败");
          }
          setBibleDiff({ open: false, current: "", proposed: "" });
        }}
        onDismiss={() => setBibleDiff({ open: false, current: "", proposed: "" })}
      />
    </div>
  );
}
