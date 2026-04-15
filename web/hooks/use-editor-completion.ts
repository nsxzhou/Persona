import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";
import { Project } from "@/lib/types";
import { api } from "@/lib/api";

export function useEditorCompletion({
  project,
  content,
  setContent,
  textareaRef,
  setBibleDiff,
}: {
  project: Project;
  content: string;
  setContent: (val: string | ((prev: string) => string)) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  setBibleDiff: (val: { open: boolean; current: string; proposed: string }) => void;
}) {
  const [isGenerating, setIsGenerating] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const rafRef = useRef<number | null>(null);

  const handleStop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    readerRef.current?.cancel();
    readerRef.current = null;
    setIsGenerating(false);
  }, []);

  const handleGenerate = async () => {
    if (!project.style_profile_id) {
      toast.error("项目未挂载风格档案，无法进行续写。请先在项目设置中选择风格档案。");
      return;
    }
    if (isGenerating) return;

    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPosition = textarea.selectionStart;
    const textBeforeCursor = content.substring(0, cursorPosition);

    setIsGenerating(true);

    try {
      const response = await api.completeEditor(project.id, textBeforeCursor);

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

      let lastFlushTime = Date.now();

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
              const detail = (() => {
                try {
                  return JSON.parse(dataStr);
                } catch {
                  return dataStr;
                }
              })();
              throw new Error(detail || "生成过程中发生错误");
            }
            try {
              const parsed = JSON.parse(dataStr);
              currentGenerated += parsed;
              needsFlush = true;
            } catch {
              // ignore
            }
          }
        }
        if (needsFlush) {
          const now = Date.now();
          if (now - lastFlushTime > 100) {
            lastFlushTime = now;
            if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
            rafRef.current = requestAnimationFrame(flushToState);
          }
        }
      }
      
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      flushToState();
      
      requestAnimationFrame(() => {
        if (textarea) {
          const newPos = cursorPosition + currentGenerated.length;
          textarea.setSelectionRange(newPos, newPos);
          textarea.focus();
        }
      });

      const MIN_LENGTH_FOR_BIBLE_UPDATE = 200;
      if (currentGenerated.trim().length >= MIN_LENGTH_FOR_BIBLE_UPDATE && project.story_bible !== undefined) {
        try {
          const { proposed_bible } = await api.proposeBibleUpdate(
            project.id,
            project.story_bible,
            currentGenerated
          );
          if (proposed_bible && proposed_bible !== project.story_bible) {
            setBibleDiff({
              open: true,
              current: project.story_bible,
              proposed: proposed_bible,
            });
          }
        } catch {
          // ignore
        }
      }

      readerRef.current = null;
    } catch (e: unknown) {
      readerRef.current = null;
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
