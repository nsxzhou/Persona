import { useCallback, useRef } from "react";

import { consumeTextEventStream } from "@/lib/sse";

export function useOutlineGenerationStream() {
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  const streamSSE = useCallback(
    async (
      fetchResponse: () => Promise<Response>,
      onChunk: (generated: string) => void,
    ) => {
      const response = await fetchResponse();
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      readerRef.current = reader;
      const generated = await consumeTextEventStream(reader, {
        onData: (_chunk, fullText) => {
          onChunk(fullText);
        },
      });

      readerRef.current = null;
      return generated;
    },
    [],
  );

  const stopGenerationStream = useCallback(() => {
    readerRef.current?.cancel();
    readerRef.current = null;
  }, []);

  return { streamSSE, stopGenerationStream };
}
