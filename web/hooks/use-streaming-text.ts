import { useCallback, useEffect, useRef } from "react";
import { consumeTextEventStream } from "@/lib/sse";

type StreamHandlers = {
  response: Response;
  onFlush: (fullText: string) => void;
  onData?: (chunk: string, fullText: string) => void;
};

function isCancellationError(error: unknown): boolean {
  return error instanceof Error && error.message === "The operation was cancelled.";
}

export function useStreamingText() {
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const rafRef = useRef<number | null>(null);
  const cancelRequestedRef = useRef(false);

  const clearScheduledFlush = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  const cancelStream = useCallback(() => {
    cancelRequestedRef.current = true;
    clearScheduledFlush();
    const reader = readerRef.current;
    readerRef.current = null;
    void reader?.cancel();
  }, [clearScheduledFlush]);

  useEffect(() => cancelStream, [cancelStream]);

  const consumeResponse = useCallback(
    async ({ response, onFlush, onData }: StreamHandlers): Promise<string> => {
      if (!response.body) throw new Error("No response body");

      cancelRequestedRef.current = false;
      const reader = response.body.getReader();
      readerRef.current = reader;

      let fullText = "";
      let lastFlushTime = Date.now();

      const flushToState = () => {
        rafRef.current = null;
        if (!cancelRequestedRef.current) {
          onFlush(fullText);
        }
      };

      try {
        await consumeTextEventStream(reader, {
          onData: (chunk, nextFullText) => {
            fullText = nextFullText;
            onData?.(chunk, nextFullText);
            if (!chunk || cancelRequestedRef.current) return;

            const now = Date.now();
            if (now - lastFlushTime > 100) {
              lastFlushTime = now;
              clearScheduledFlush();
              rafRef.current = requestAnimationFrame(flushToState);
            }
          },
        });

        clearScheduledFlush();
        if (!cancelRequestedRef.current) {
          flushToState();
        }
        return fullText;
      } catch (error: unknown) {
        if (isCancellationError(error)) {
          return fullText;
        }
        throw error;
      } finally {
        readerRef.current = null;
        clearScheduledFlush();
      }
    },
    [clearScheduledFlush],
  );

  return { consumeResponse, cancelStream };
}
