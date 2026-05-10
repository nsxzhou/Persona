import { useCallback, useState } from "react";
import { toast } from "sonner";
import { Project, ProjectBible } from "@/lib/types";
import { api } from "@/lib/api";
import type { RegenerateOptions } from "@/lib/api-client";
import { useStreamingText } from "@/hooks/use-streaming-text";
import { useEditorContext } from "@/components/editor/editor-context";

export function useBeatGeneration({
  project,
  projectBible,
  textareaRef,
  isGenerating,
  currentChapterContext,
  previousChapterContext = "",
  totalContentLength = 0,
  chapterId = null,
  disabled = false,
  onBeatExpandCompleted,
}: {
  project: Project;
  projectBible: ProjectBible;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  isGenerating: boolean;
  currentChapterContext?: string;
  previousChapterContext?: string;
  totalContentLength?: number;
  chapterId?: string | null;
  disabled?: boolean;
  onBeatExpandCompleted?: (generated: string) => Promise<void> | void;
}) {
  const [beats, setBeats] = useState<string[]>([]);
  const [currentBeatIndex, setCurrentBeatIndex] = useState(-1);
  const [isGeneratingBeats, setIsGeneratingBeats] = useState(false);
  const [isExpandingBeat, setIsExpandingBeat] = useState(false);
  const { consumeResponse } = useStreamingText();
  const { store } = useEditorContext();

  const handleGenerateBeats = useCallback(async (options?: RegenerateOptions) => {
    if (isGeneratingBeats || disabled) return;
    setIsGeneratingBeats(true);
    try {
      const content = store.getState().content;
      const textarea = textareaRef.current;
      const textBeforeCursor = textarea
        ? content.substring(0, textarea.selectionStart)
        : content;

      const data = await api.runBeatsWorkflow(
        project.id,
        chapterId,
        textBeforeCursor,
        projectBible.runtime_state ?? "",
        projectBible.runtime_threads ?? "",
        projectBible.outline_detail ?? "",
        currentChapterContext,
        previousChapterContext,
        totalContentLength,
        options,
      );

      setBeats(data.beats);
      setCurrentBeatIndex(-1);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "生成节拍失败");
    } finally {
      setIsGeneratingBeats(false);
    }
  }, [chapterId, currentChapterContext, disabled, isGeneratingBeats, previousChapterContext, project.id, projectBible.outline_detail, projectBible.runtime_state, projectBible.runtime_threads, store, textareaRef, totalContentLength]);

  const handleStartBeatExpand = useCallback(async (options?: RegenerateOptions) => {
    const content = store.getState().content;
    if (beats.length === 0 || isExpandingBeat || isGenerating || disabled) return;
    if (!options && content.trim() && !window.confirm("当前章节已有正文，继续将替换本章正文。")) {
      return;
    }

    const textBeforeCursor = "";
    const textAfterCursor = "";
    setCurrentBeatIndex(0);
    setIsExpandingBeat(true);

    let chapterProse = "";
    try {
      const { response, reviewIssues } = await api.runChapterExpandWorkflow(
        project.id,
        chapterId,
        textBeforeCursor,
        projectBible.runtime_state ?? "",
        projectBible.runtime_threads ?? "",
        projectBible.outline_detail ?? "",
        beats,
        currentChapterContext,
        previousChapterContext,
        project.style_profile_id,
        project.plot_profile_id,
        options,
      );

      chapterProse = await consumeResponse({
        response,
        onFlush: (fullText) => {
          const newContent = textBeforeCursor + fullText + textAfterCursor;
          store.getState().setContent(newContent);
        },
      });
      if (reviewIssues.length > 0) {
        toast.message(`章节审校提示：${reviewIssues.join("；")}`);
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "展开失败";
      if (message !== "The operation was cancelled.") {
        toast.error(message);
      }
    } finally {
      setIsExpandingBeat(false);
      setCurrentBeatIndex(-1);
    }
    if (chapterProse.trim()) await onBeatExpandCompleted?.(chapterProse);
  }, [beats, chapterId, consumeResponse, currentChapterContext, disabled, isExpandingBeat, isGenerating, onBeatExpandCompleted, previousChapterContext, project.id, project.plot_profile_id, project.style_profile_id, projectBible.outline_detail, projectBible.runtime_state, projectBible.runtime_threads, store]);

  return {
    beats,
    setBeats,
    currentBeatIndex,
    isGeneratingBeats,
    isExpandingBeat,
    handleGenerateBeats,
    handleStartBeatExpand,
  };
}
