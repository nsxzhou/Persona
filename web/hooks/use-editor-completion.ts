import { useCallback, useState } from "react";
import { toast } from "sonner";
import { Project } from "@/lib/types";
import { api } from "@/lib/api";
import { useStreamingText } from "@/hooks/use-streaming-text";
import { useEditorStore } from "@/components/editor/editor-store";

export function useEditorCompletion({
  project,
  textareaRef,
  onGeneratedContent,
  currentChapterContext = "",
  previousChapterContext = "",
  totalContentLength = 0,
  disabled = false,
}: {
  project: Project;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  onGeneratedContent?: (generated: string) => Promise<void> | void;
  currentChapterContext?: string;
  previousChapterContext?: string;
  totalContentLength?: number;
  disabled?: boolean;
}) {
  const [isGenerating, setIsGenerating] = useState(false);
  const { consumeResponse, cancelStream } = useStreamingText();

  const handleStop = useCallback(() => {
    cancelStream();
    setIsGenerating(false);
  }, [cancelStream]);

  const handleGenerate = async () => {
    if (!project.style_profile_id) {
      toast.error("项目未挂载风格档案，无法进行续写。请先在项目设置中选择风格档案。");
      return;
    }
    if (!project.generation_profile?.genre_mother || !project.generation_profile?.intensity_level) {
      toast.error("项目未配置 generation profile，无法进行正式生成。请先在项目设置中完成题材与强度设置。");
      return;
    }
    if (isGenerating || disabled) return;

    const textarea = textareaRef.current;
    if (!textarea) return;

    const content = useEditorStore.getState().content;
    const cursorPosition = textarea.selectionStart;
    const textBeforeCursor = content.substring(0, cursorPosition);
    const textAfterCursor = content.substring(cursorPosition);

    setIsGenerating(true);

    try {
      const response = await api.completeEditor(
        project.id,
        textBeforeCursor,
        currentChapterContext,
        previousChapterContext,
        totalContentLength,
        project.generation_profile,
      );

      const currentGenerated = await consumeResponse({
        response,
        onFlush: (fullText) => {
          useEditorStore.getState().setContent(`${textBeforeCursor}${fullText}${textAfterCursor}`);
        },
      });

      requestAnimationFrame(() => {
        if (textarea) {
          const newPos = cursorPosition + currentGenerated.length;
          textarea.setSelectionRange(newPos, newPos);
          textarea.focus();
        }
      });

      if (currentGenerated.trim()) {
        await onGeneratedContent?.(currentGenerated);
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "请求失败";
      if (message !== "The operation was cancelled.") {
        toast.error(message);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  return { isGenerating, handleGenerate, handleStop };
}
