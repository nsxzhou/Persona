import type { ConceptGenerateResult } from "@/lib/types";

export function buildSseResponse(text: string): Response {
  const payload = `data: ${JSON.stringify(text)}\n\n`;
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(payload));
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { "content-type": "text/event-stream" },
  });
}

export function parseMarkdownConcepts(markdown: string): ConceptGenerateResult {
  const headings = Array.from(markdown.matchAll(/^###\s+([^\n]+)\s*$/gm));
  const concepts = headings
    .map((match, index) => {
      const title = match[1].trim().replace(/^\d+[.、\s]+/, "");
      const synopsisStart = (match.index ?? 0) + match[0].length;
      const synopsisEnd = headings[index + 1]?.index ?? markdown.length;
      const synopsis = markdown.slice(synopsisStart, synopsisEnd).trim();
      return { title, synopsis };
    })
    .filter((item) => item.title && item.synopsis);
  return { concepts };
}

export function parseMemoryBundle(markdown: string): {
  proposedCharactersStatus: string;
  proposedRuntimeState: string;
  proposedRuntimeThreads: string;
} {
  const sections = new Map<string, string>();
  const regex = /^##\s+([^\n]+)\n([\s\S]*?)(?=^##\s+|\Z)/gm;
  for (const match of markdown.matchAll(regex)) {
    sections.set(match[1].trim(), match[2].trim());
  }
  return {
    proposedCharactersStatus: sections.get("角色动态状态") ?? "",
    proposedRuntimeState: sections.get("运行时状态") ?? "",
    proposedRuntimeThreads: sections.get("伏笔与线索追踪") ?? "",
  };
}
