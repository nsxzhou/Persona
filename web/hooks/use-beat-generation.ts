import { useRef, useState } from "react";
import { toast } from "sonner";
import { Project } from "@/lib/types";
import { api } from "@/lib/api";
import { consumeTextEventStream } from "@/lib/sse";

export function useBeatGeneration({
  project,
  content,
  setContent,
  textareaRef,
  isGenerating,
  currentChapterContext,
  previousChapterContext = "",
  totalContentLength = 0,
  disabled = false,
  onGeneratedContent,
}: {
  project: Project;
  content: string;
  setContent: (val: string | ((prev: string) => string)) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  isGenerating: boolean;
  currentChapterContext?: string;
  previousChapterContext?: string;
  totalContentLength?: number;
  disabled?: boolean;
  onGeneratedContent?: (generated: string) => void;
}) {
  const [beats, setBeats] = useState<string[]>([]);
  const [currentBeatIndex, setCurrentBeatIndex] = useState(-1);
  const [isGeneratingBeats, setIsGeneratingBeats] = useState(false);
  const [isExpandingBeat, setIsExpandingBeat] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const rafRef = useRef<number | null>(null);

  const handleGenerateBeats = async () => {
    if (isGeneratingBeats || disabled) return;
    setIsGeneratingBeats(true);
    try {
      const textarea = textareaRef.current;
      const textBeforeCursor = textarea
        ? content.substring(0, textarea.selectionStart)
        : content;

      const data = await api.generateBeats(
        project.id,
        textBeforeCursor,
        project.runtime_state ?? "",
        project.runtime_threads ?? "",
        project.outline_detail ?? "",
        currentChapterContext,
        previousChapterContext,
        totalContentLength,
      );

      setBeats(data.beats);
      setCurrentBeatIndex(-1);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "生成节拍失败");
    } finally {
      setIsGeneratingBeats(false);
    }
  };

  const handleStartBeatExpand = async () => {
    if (beats.length === 0 || isExpandingBeat || isGenerating || disabled) return;
    if (content.trim() && !window.confirm("当前章节已有正文，继续将替换本章正文。")) return;

    const textBeforeCursor = "";
    const textAfterCursor = "";

    let beatsProse = "";
    for (let i = 0; i < beats.length; i++) {
      setCurrentBeatIndex(i);
      setIsExpandingBeat(true);

      try {
        const response = await api.expandBeat(
          project.id,
          textBeforeCursor,
          project.runtime_state ?? "",
          project.runtime_threads ?? "",
          project.outline_detail ?? "",
          beats[i],
          i,
          beats.length,
          beatsProse,
          currentChapterContext,
          previousChapterContext,
        );

        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        readerRef.current = reader;
        let beatGenerated = "";
        let needsFlush = false;

        const flushToState = () => {
          rafRef.current = null;
          const newContent = textBeforeCursor + beatsProse + beatGenerated + textAfterCursor;
          setContent(newContent);
          needsFlush = false;
        };

        let lastFlushTime = Date.now();
        await consumeTextEventStream(reader, {
          onData: (chunk, fullText) => {
            beatGenerated = fullText;
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
    if (beatsProse.trim()) onGeneratedContent?.(beatsProse);
  };

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
