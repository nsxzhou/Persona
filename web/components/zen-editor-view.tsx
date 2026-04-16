"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Project } from "@/lib/types";
import {
  ArrowLeft,
  BookOpen,
  ListOrdered,
  Loader2,
  Settings,
  Sparkles,
  Square,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { NAV_ITEMS } from "@/components/app-shell";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export function ZenEditorView({
  project,
  activeProfileName,
  initialChapterSelection = null,
  initialIntent = null,
}: {
  project: Project;
  activeProfileName?: string;
  initialChapterSelection?: { volumeIndex: number; chapterIndex: number } | null;
  initialIntent?: "navigate" | "generate_beats" | null;
}) {
  const router = useRouter();
  const [content, setContent] = useState(project.content || "");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [bibleDiff, setBibleDiff] = useState<{
    open: boolean;
    current: string;
    proposed: string;
  }>({ open: false, current: "", proposed: "" });

  const [projectData, setProjectData] = useState(project);

  // Panel state
  const [isLeftExpanded, setIsLeftExpanded] = useState(Boolean(initialChapterSelection));
  const [isRightExpanded, setIsRightExpanded] = useState(initialIntent === "generate_beats");

  // Chapter navigation state
  const [currentChapter, setCurrentChapter] = useState<{
    volumeIndex: number;
    chapterIndex: number;
  } | null>(initialChapterSelection);
  const [selectedVolumeIndex, setSelectedVolumeIndex] = useState<number | null>(
    initialChapterSelection?.volumeIndex ?? null,
  );
  const [chapterFocusMode, setChapterFocusMode] = useState<"idle" | "navigate" | "generate_beats">(
    initialChapterSelection ? (initialIntent ?? "navigate") : "idle",
  );

  const parsedOutline = useMemo(
    () => parseOutline(projectData.outline_detail),
    [projectData.outline_detail],
  );

  const completedChapters = useMemo(() => {
    const set = new Set<string>();
    const regex = /^# (.+)$/gm;
    let match;
    while ((match = regex.exec(content)) !== null) {
      set.add(match[1].trim());
    }
    return set;
  }, [content]);

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
    setIsRightExpanded(true);
    setTimeout(() => handleGenerateBeats(), 100);
  }, [handleGenerateBeats]);

  const handleSelectChapter = useCallback((volumeIndex: number, chapterIndex: number) => {
    setSelectedVolumeIndex(volumeIndex);
    setCurrentChapter({ volumeIndex, chapterIndex });
    setChapterFocusMode("navigate");
    setIsLeftExpanded(true);
  }, []);

  useEffect(() => {
    if (selectedVolumeIndex === null) return;

    const volume = parsedOutline.volumes[selectedVolumeIndex];
    if (!volume) {
      setSelectedVolumeIndex(null);
      setCurrentChapter(null);
      setChapterFocusMode("idle");
      return;
    }

    if (!currentChapter) return;
    const chapter = volume.chapters[currentChapter.chapterIndex];
    if (!chapter) {
      setCurrentChapter(null);
    }
  }, [currentChapter, parsedOutline, selectedVolumeIndex]);

  // Responsive defaults
  useEffect(() => {
    const width = window.innerWidth;
    if (width < 1024) {
      setIsLeftExpanded(false);
      setIsRightExpanded(false);
    } else if (width < 1280) {
      if (!initialChapterSelection) setIsLeftExpanded(false);
      if (initialIntent !== "generate_beats") setIsRightExpanded(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Mutex mode for narrow screens
  const toggleLeft = useCallback(() => {
    setIsLeftExpanded((prev) => {
      const next = !prev;
      if (next && window.innerWidth < 1024) setIsRightExpanded(false);
      return next;
    });
  }, []);

  const toggleRight = useCallback(() => {
    setIsRightExpanded((prev) => {
      const next = !prev;
      if (next && window.innerWidth < 1024) setIsLeftExpanded(false);
      return next;
    });
  }, []);

  const currentVolumeTitle = selectedVolumeIndex !== null
    ? getVolumeTitle(parsedOutline.volumes[selectedVolumeIndex]?.title ?? "")
    : null;
  const currentChapterTitle = currentChapter
    ? parsedOutline.volumes[currentChapter.volumeIndex]?.chapters[currentChapter.chapterIndex]?.title ?? null
    : null;
  const currentVolumeHasChapters = selectedVolumeIndex !== null
    ? (parsedOutline.volumes[selectedVolumeIndex]?.chapters.length ?? 0) > 0
    : true;
  const currentChapterStatus = currentChapter
    ? chapterFocusMode === "generate_beats"
      ? "已定位章节，准备生成节拍"
      : "已定位章节"
    : "请从左侧创作导航选择章节";
  const missingOutlineStatus = selectedVolumeIndex !== null && !currentVolumeHasChapters;

  const handleGoGenerateVolume = useCallback(
    (volumeIndex: number) => {
      router.push(`/projects/${project.id}?tab=outline_detail&volumeIndex=${volumeIndex}`);
    },
    [project.id, router],
  );

  const chapterBannerAction = missingOutlineStatus && selectedVolumeIndex !== null ? (
    <Button variant="outline" size="sm" onClick={() => handleGoGenerateVolume(selectedVolumeIndex)}>
      去生成本卷章节细纲
    </Button>
  ) : currentChapter ? (
    <Button className="gap-2" size="sm" onClick={handleGenerateBeatsForChapter}>
      <Sparkles className="h-4 w-4" />
      为当前章节生成节拍
    </Button>
  ) : (
    <Button variant="outline" size="sm" onClick={toggleLeft}>
      打开创作导航
    </Button>
  );

  // Dynamic max-width for writing area
  const editorMaxWidth = isLeftExpanded && isRightExpanded
    ? "max-w-[600px]"
    : isLeftExpanded || isRightExpanded
      ? "max-w-[680px]"
      : "max-w-[720px]";

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Escape" && isGenerating) {
      e.preventDefault();
      handleStop();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "b") {
      e.preventDefault();
      toggleLeft();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "j") {
      e.preventDefault();
      toggleRight();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "j") {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      {/* Icon Rail */}
      <div className="w-12 shrink-0 bg-[#111] flex flex-col items-center pt-3 gap-1">
        {/* Logo / Quick Menu */}
        <Popover>
          <PopoverTrigger asChild>
            <button
              type="button"
              className="w-8 h-8 bg-primary flex items-center justify-center mb-3 hover:opacity-90 transition-opacity"
              title="快速导航"
            >
              <span className="text-primary-foreground font-black text-sm">P</span>
            </button>
          </PopoverTrigger>
          <PopoverContent side="right" align="start" className="w-48 p-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </Link>
            ))}
          </PopoverContent>
        </Popover>

        {/* 创作导航 toggle */}
        <button
          type="button"
          onClick={toggleLeft}
          className={`w-9 h-9 flex items-center justify-center transition-colors ${
            isLeftExpanded ? "bg-white/15" : "hover:bg-white/10"
          }`}
          title="创作导航 (⌘B)"
        >
          <BookOpen className="h-[18px] w-[18px] text-white" />
        </button>

        {/* 创作设定 toggle */}
        <button
          type="button"
          onClick={() => {
            if (!isLeftExpanded) setIsLeftExpanded(true);
          }}
          className="w-9 h-9 flex items-center justify-center opacity-50 hover:opacity-80 transition-opacity"
          title="创作设定"
        >
          <Settings className="h-[18px] w-[18px] text-white" />
        </button>

        <div className="flex-1" />

        {/* Back to project */}
        <button
          type="button"
          onClick={() => router.push(`/projects/${project.id}`)}
          className="w-9 h-9 flex items-center justify-center opacity-50 hover:opacity-80 transition-opacity mb-3"
          title="返回项目工作台"
        >
          <ArrowLeft className="h-[18px] w-[18px] text-white" />
        </button>
      </div>

      {/* Left Panel: 创作导航 */}
      <div
        className="shrink-0 overflow-hidden transition-[width] duration-200 ease-in-out"
        style={{ width: isLeftExpanded ? 260 : 0 }}
      >
        {isLeftExpanded && (
          <EditorSidePanel
            project={projectData}
            contentLength={content.length}
            parsedOutline={parsedOutline}
            currentChapter={currentChapter}
            completedChapters={completedChapters}
            onSelectChapter={handleSelectChapter}
            onGenerateBeatsForChapter={handleGenerateBeatsForChapter}
            onGoGenerateVolume={handleGoGenerateVolume}
            onCollapse={() => setIsLeftExpanded(false)}
            onFieldChange={(field, value) => setProjectData((prev) => ({ ...prev, [field]: value }))}
          />
        )}
      </div>

      {/* Center Column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="border-b shrink-0">
          <div className="flex items-center justify-between px-6 py-3">
            <div className="flex items-center gap-4">
              <h1 className="text-lg font-medium">{project.name}</h1>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>保存中...</span>
                  </>
                ) : (
                  <span>已保存</span>
                )}
              </div>
              {activeProfileName && (
                <div className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-1.5 text-sm">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <span className="font-medium">{activeProfileName}</span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-3">
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
                  AI 续写 (⌘J)
                </Button>
              )}
            </div>
          </div>

          {/* Chapter Context Banner */}
          <div className="px-6 pb-3">
            <div className="flex flex-col gap-3 rounded-xl border border-border bg-muted/30 px-4 py-3 md:flex-row md:items-center md:justify-between">
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  当前章节
                </p>
                {missingOutlineStatus ? (
                  <>
                    <p className="text-sm font-medium text-foreground">当前分卷尚未生成章节细纲</p>
                    <p className="text-xs text-muted-foreground">
                      请先回到「分卷与章节细纲」页为该分卷生成章节细纲
                    </p>
                  </>
                ) : currentChapter && currentChapterTitle ? (
                  <>
                    <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                      <span>{currentVolumeTitle}</span>
                      <span>/</span>
                      <span className="font-medium text-foreground">{currentChapterTitle}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{currentChapterStatus}</p>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-medium text-foreground">未选择章节</p>
                    <p className="text-xs text-muted-foreground">{currentChapterStatus}</p>
                  </>
                )}
              </div>
              <div className="shrink-0">{chapterBannerAction}</div>
            </div>
          </div>
        </header>

        {/* Writing Area */}
        <main className="flex-1 overflow-hidden flex justify-center bg-muted/20">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="开始创作... (按 ⌘J 进行 AI 续写)"
            className={`w-full ${editorMaxWidth} h-full p-8 md:p-12 resize-none bg-transparent outline-none text-lg leading-relaxed shadow-none border-none focus:ring-0 text-foreground/90 placeholder:text-muted-foreground/50`}
            style={{
              fontFamily: "var(--font-serif), serif",
            }}
          />
        </main>
      </div>

      {/* Right Panel: 节拍写作 */}
      {isRightExpanded ? (
        <div
          className="shrink-0 overflow-hidden transition-[width] duration-200 ease-in-out"
          style={{ width: 280 }}
        >
          <BeatPanel
            beats={beats}
            currentBeatIndex={currentBeatIndex}
            isExpandingBeat={isExpandingBeat}
            isGeneratingBeats={isGeneratingBeats}
            onGenerateBeats={handleGenerateBeats}
            onBeatsChange={setBeats}
            onStartExpand={handleStartBeatExpand}
            onClose={() => setIsRightExpanded(false)}
          />
        </div>
      ) : (
        /* Collapsed right rail */
        <button
          type="button"
          onClick={toggleRight}
          className="w-12 shrink-0 border-l border-border bg-background flex flex-col items-center pt-3 gap-2 hover:bg-muted/30 transition-colors cursor-pointer"
          title="展开节拍写作 (⌘⇧J)"
        >
          <ListOrdered className="h-[18px] w-[18px] text-muted-foreground" />
          <span
            className="text-[10px] text-muted-foreground tracking-widest mt-2"
            style={{ writingMode: "vertical-rl" }}
          >
            节拍写作
          </span>
          <div className="flex-1" />
          {beats.length > 0 && (
            <span className="text-[10px] text-primary font-semibold mb-3">
              {Math.max(currentBeatIndex + 1, 1)}/{beats.length}
            </span>
          )}
        </button>
      )}

      {/* Bible Diff Dialog */}
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

function getVolumeTitle(title: string) {
  return title.trim() || "未分卷章节";
}
