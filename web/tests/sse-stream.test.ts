import { describe, expect, test } from "vitest";

import { consumeTextEventStream } from "@/lib/sse";

function createStream(chunks: string[]) {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      const encoder = new TextEncoder();
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

describe("consumeTextEventStream", () => {
  test("emits parsed text chunks across split frames", async () => {
    const stream = createStream([
      'data: "hello',
      '"\n\n',
      'data: " world"\n\n',
    ]);
    const reader = stream.getReader();
    const received: string[] = [];

    const result = await consumeTextEventStream(reader, {
      onData: (chunk) => {
        received.push(chunk);
      },
    });

    expect(received).toEqual(["hello", " world"]);
    expect(result).toBe("hello world");
  });

  test("throws event error payload as message", async () => {
    const stream = createStream(['event: error\ndata: "boom"\n\n']);
    const reader = stream.getReader();

    await expect(consumeTextEventStream(reader, {})).rejects.toThrow("boom");
  });
});
