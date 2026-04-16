import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";
import { Project } from "@/lib/types";
import { api } from "@/lib/api";
import { consumeTextEventStream } from "@/lib/sse";

export function useEditorCompletion({
  project,
  content,
  setContent,
  textareaRef,
  setBibleDiff,
  currentChapterContext = "",
  previousChapterContext = "",
  totalContentLength = 0,
  disabled = false,
}: {
  project: Project;
  content: string;
  setContent: (val: string | ((prev: string) => string)) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  setBibleDiff: (val: {
    open: boolean;
    currentState: string;
    proposedState: string;
    currentThreads: string;
    proposedThreads: string;
  }) => void;
  currentChapterContext?: string;
  previousChapterContext?: string;
  totalContentLength?: number;
  disabled?: boolean;
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
    if (isGenerating || disabled) return;

    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPosition = textarea.selectionStart;
    const textBeforeCursor = content.substring(0, cursorPosition);

    setIsGenerating(true);

    try {
      const response = await api.completeEditor(
        project.id,
        textBeforeCursor,
        currentChapterContext,
        previousChapterContext,
        totalContentLength,
      );

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      readerRef.current = reader;

      let currentGenerated = "";
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
      await consumeTextEventStream(reader, {
        onData: (chunk, fullText) => {
          currentGenerated = fullText;
          if (!chunk) return;
          needsFlush = true;
          const now = Date.now();
          if (now - lastFlushTime > 100) {
            lastFlushTime = now;
            if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
            rafRef.current = requestAnimationFrame(flushToState);
          }
        },
      });
      
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
      if (currentGenerated.trim().length >= MIN_LENGTH_FOR_BIBLE_UPDATE && project.runtime_state !== undefined) {
        try {
          const { proposed_runtime_state, proposed_runtime_threads } = await api.proposeBibleUpdate(
            project.id,
            project.runtime_state,
            project.runtime_threads ?? "",
            currentGenerated
          );
          const stateChanged = proposed_runtime_state && proposed_runtime_state !== project.runtime_state;
          const threadsChanged = proposed_runtime_threads && proposed_runtime_threads !== (project.runtime_threads ?? "");
          if (stateChanged || threadsChanged) {
            setBibleDiff({
              open: true,
              currentState: project.runtime_state,
              proposedState: proposed_runtime_state,
              currentThreads: project.runtime_threads ?? "",
              proposedThreads: proposed_runtime_threads,
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
