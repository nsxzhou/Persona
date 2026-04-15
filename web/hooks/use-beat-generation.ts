import { useRef, useState } from "react";
import { toast } from "sonner";
import { Project } from "@/lib/types";

export function useBeatGeneration({
  project,
  content,
  setContent,
  textareaRef,
  isGenerating,
}: {
  project: Project;
  content: string;
  setContent: (val: string | ((prev: string) => string)) => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  isGenerating: boolean;
}) {
  const [beats, setBeats] = useState<string[]>([]);
  const [currentBeatIndex, setCurrentBeatIndex] = useState(-1);
  const [isGeneratingBeats, setIsGeneratingBeats] = useState(false);
  const [isExpandingBeat, setIsExpandingBeat] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const rafRef = useRef<number | null>(null);

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
