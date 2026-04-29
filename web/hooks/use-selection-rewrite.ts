import { useCallback, useState } from "react";
import type { RefObject } from "react";
import { toast } from "sonner";

import { useEditorContext } from "@/components/editor/editor-context";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";

type SelectionSnapshot = {
  start: number;
  end: number;
  selectedText: string;
  textBeforeSelection: string;
  textAfterSelection: string;
};

export function useSelectionRewrite({
  project,
  textareaRef,
  currentChapterContext = "",
  previousChapterContext = "",
  totalContentLength = 0,
  disabled = false,
}: {
  project: Project;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  currentChapterContext?: string;
  previousChapterContext?: string;
  totalContentLength?: number;
  disabled?: boolean;
}) {
  const { store } = useEditorContext();
  const [selection, setSelection] = useState<SelectionSnapshot | null>(null);
  const [instruction, setInstruction] = useState("");
  const [preview, setPreview] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const openRewrite = useCallback(() => {
    if (disabled || isGenerating) return;
    if (!project.style_profile_id) {
      toast.error("项目未挂载风格档案，无法进行局部改写。请先在项目设置中选择风格档案。");
      return;
    }
    if (!project.generation_profile?.genre_mother || !project.generation_profile?.intensity_level) {
      toast.error("项目未配置 generation profile，无法进行正式生成。请先在项目设置中完成题材与强度设置。");
      return;
    }

    const textarea = textareaRef.current;
    if (!textarea) return;

    const content = store.getState().content;
    const start = Math.min(textarea.selectionStart, textarea.selectionEnd);
    const end = Math.max(textarea.selectionStart, textarea.selectionEnd);
    const selectedText = content.slice(start, end);
    if (!selectedText.trim()) {
      toast.message("请先选择要修改的文本");
      return;
    }

    setSelection({
      start,
      end,
      selectedText,
      textBeforeSelection: content.slice(0, start),
      textAfterSelection: content.slice(end),
    });
    setInstruction("");
    setPreview("");
    setIsOpen(true);
  }, [disabled, isGenerating, project.generation_profile, project.style_profile_id, store, textareaRef]);

  const closeRewrite = useCallback(() => {
    if (isGenerating) return;
    setIsOpen(false);
    setSelection(null);
    setInstruction("");
    setPreview("");
  }, [isGenerating]);

  const generatePreview = useCallback(async () => {
    if (!selection || isGenerating) return;
    const trimmedInstruction = instruction.trim();
    if (!trimmedInstruction) {
      toast.message("请输入修改要求");
      return;
    }

    setIsGenerating(true);
    try {
      const rewritten = await api.runSelectionRewriteWorkflow({
        projectId: project.id,
        selectedText: selection.selectedText,
        textBeforeSelection: selection.textBeforeSelection,
        textAfterSelection: selection.textAfterSelection,
        rewriteInstruction: trimmedInstruction,
        currentChapterContext,
        previousChapterContext,
        totalContentLength,
        generationProfile: project.generation_profile,
      });
      setPreview(rewritten);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "局部改写失败");
    } finally {
      setIsGenerating(false);
    }
  }, [
    currentChapterContext,
    instruction,
    isGenerating,
    previousChapterContext,
    project.generation_profile,
    project.id,
    selection,
    totalContentLength,
  ]);

  const applyPreview = useCallback(() => {
    if (!selection || !preview) return;

    const content = store.getState().content;
    const nextContent = `${content.slice(0, selection.start)}${preview}${content.slice(selection.end)}`;
    store.getState().setContent(nextContent);

    requestAnimationFrame(() => {
      const textarea = textareaRef.current;
      if (!textarea) return;
      const nextPosition = selection.start + preview.length;
      textarea.setSelectionRange(nextPosition, nextPosition);
      textarea.focus();
    });

    setIsOpen(false);
    setSelection(null);
    setInstruction("");
    setPreview("");
  }, [preview, selection, store, textareaRef]);

  return {
    isOpen,
    isGenerating,
    selection,
    instruction,
    setInstruction,
    preview,
    openRewrite,
    closeRewrite,
    generatePreview,
    applyPreview,
  };
}
