export type ConsumeTextEventStreamOptions = {
  onData?: (chunk: string, fullText: string) => void;
};

function parseSseErrorPayload(payload: string): string {
  try {
    return JSON.parse(payload) as string;
  } catch {
    return payload;
  }
}

export async function consumeTextEventStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  options: ConsumeTextEventStreamOptions = {},
): Promise<string> {
  const decoder = new TextDecoder();
  let buffer = "";
  let generated = "";
  let pendingError = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const lines = frame.split("\n");
        let dataPayload = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            pendingError = line.slice(7).trim() === "error";
          } else if (line.startsWith("data: ")) {
            dataPayload += line.slice(6);
          }
        }

        if (!dataPayload) continue;
        if (pendingError) {
          throw new Error(parseSseErrorPayload(dataPayload) || "生成过程中发生错误");
        }

        try {
          const chunk = JSON.parse(dataPayload) as string;
          generated += chunk;
          options.onData?.(chunk, generated);
        } catch {
          // Ignore malformed partial payloads and continue consuming the stream.
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  return generated;
}
