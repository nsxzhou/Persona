"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { Project } from "@/lib/types";
import { ArrowLeft, BookOpen, ListOrdered, Sparkles, Square, Loader2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { EditorSidePanel } from "@/components/editor-side-panel";
import { BibleDiffDialog } from "@/components/bible-diff-dialog";
import { BeatPanel } from "@/components/beat-panel";
import { useEditorAutosave } from "@/hooks/use-editor-autosave";
import { useEditorCompletion } from "@/hooks/use-editor-completion";
import { useBeatGeneration } from "@/hooks/use-beat-generation";
import { parseOutline } from "@/lib/outline-parser";

export function ZenEditorView({
  project,
  activeProfileName,
}: {
  project: Project;
  activeProfileName?: string;
}) {
  const [content, setContent] = useState(project.content || "");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [bibleDiff, setBibleDiff] = useState<{
    open: boolean;
    current: string;
    proposed: string;
  }>({ open: false, current: "", proposed: "" });

  // Mutable project data for bible fields (so side panel reflects updates)
  const [projectData, setProjectData] = useState(project);

  // Chapter navigation state
  const [currentChapter, setCurrentChapter] = useState<{
    volumeIndex: number;
    chapterIndex: number;
  } | null>(null);

  const parsedOutline = useMemo(
    () => parseOutline(projectData.outline_detail),
    [projectData.outline_detail],
  );

  // Compute completed chapters by scanning content for chapter heading markers
  const completedChapters = useMemo(() => {
    const set = new Set<string>();
    const regex = /^# (.+)$/gm;
    let match;
    while ((match = regex.exec(content)) !== null) {
      set.add(match[1].trim());
    }
    return set;
  }, [content]);

  // Build chapter context string for Beat generation
  const currentChapterContext = useMemo(() => {
    if (!currentChapter || !parsedOutline.volumes.length) return "";
    const vol = parsedOutline.volumes[currentChapter.volumeIndex];
    if (!vol) return "";
    const ch = vol.chapters[currentChapter.chapterIndex];
    if (!ch) return "";
    const parts = [`**${ch.title}**`];
    if (ch.coreEvent) parts.push(`- 核心事件：${ch.coreEvent}`);
    if (ch.emotionArc) parts.push(`- 情绪走向：${ch.emotionArc}`);
    if (ch.chapterHook) parts.push(`- 章末钩子：${ch.chapterHook}`);
    return parts.join("\n");
  }, [currentChapter, parsedOutline]);

  const { isGenerating, handleGenerate, handleStop } = useEditorCompletion({
    project: projectData,
    content,
    setContent,
    textareaRef,
    setBibleDiff,
  });

  // ---- Beat mode ----
  const [isBeatPanelOpen, setIsBeatPanelOpen] = useState(false);
  const {
    beats,
    setBeats,
    currentBeatIndex,
    isGeneratingBeats,
    isExpandingBeat,
    handleGenerateBeats,
    handleStartBeatExpand,
  } = useBeatGeneration({
    project: projectData,
    content,
    setContent,
    textareaRef,
    isGenerating,
    currentChapterContext,
  });

  const { isSaving } = useEditorAutosave(
    project.id,
    content,
    project.content,
    isGenerating || isExpandingBeat
  );

  const handleGenerateBeatsForChapter = useCallback(() => {
    setIsBeatPanelOpen(true);
    // Trigger beat generation after panel opens
    setTimeout(() => handleGenerateBeats(), 100);
  }, [handleGenerateBeats]);

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
            title="创作导航 (Cmd+B)"
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
            contentLength={content.length}
            parsedOutline={parsedOutline}
            currentChapter={currentChapter}
            completedChapters={completedChapters}
            onSelectChapter={(vi, ci) => setCurrentChapter({ volumeIndex: vi, chapterIndex: ci })}
            onGenerateBeatsForChapter={handleGenerateBeatsForChapter}
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
