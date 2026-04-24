export interface ParsedChapter {
  title: string;
  coreEvent: string;
  emotionArc: string;
  chapterHook: string;
  rawMarkdown: string;
}

export interface ParsedVolume {
  title: string;
  meta: string;
  chapters: ParsedChapter[];
}

export interface ParsedOutline {
  volumes: ParsedVolume[];
  parseErrors: string[];
}

function extractField(text: string, fieldName: string): string {
  const re = new RegExp(`\\*\\*${fieldName}\\*\\*[：:]\\s*(.+)`);
  const m = text.match(re);
  return m ? m[1].trim() : "";
}

function extractFirstField(text: string, fieldNames: string[]): string {
  for (const fieldName of fieldNames) {
    const value = extractField(text, fieldName);
    if (value) return value;
  }
  return "";
}

function parseChapter(block: string): ParsedChapter {
  const lines = block.split("\n");
  const titleLine = lines[0] ?? "";
  const title = titleLine.replace(/^###\s*/, "").trim();

  return {
    title,
    coreEvent: extractField(block, "核心事件"),
    emotionArc: extractField(block, "情绪走向"),
    chapterHook: extractFirstField(block, ["章末钩子", "章节末推动点"]),
    rawMarkdown: block.trim(),
  };
}

function parseVolumeBlock(block: string, title: string): ParsedVolume {
  const lines = block.split("\n");

  // Extract meta from blockquote line (> ...)
  let meta = "";
  for (const line of lines) {
    const bq = line.match(/^>\s*(.+)/);
    if (bq) {
      meta = bq[1].trim();
      break;
    }
  }

  // Split into chapter blocks by ### headings
  const chapterBlocks: string[] = [];
  const chapterSplitParts = block.split(/(?=^### )/m);

  for (const part of chapterSplitParts) {
    if (part.match(/^### /)) {
      chapterBlocks.push(part.trimEnd());
    }
  }

  const chapters = chapterBlocks.map(parseChapter);

  return { title, meta, chapters };
}

export function parseOutline(markdown: string): ParsedOutline {
  const trimmed = markdown.trim();

  if (trimmed === "") {
    return { volumes: [], parseErrors: [] };
  }

  // Check if we have ## volume headings
  const hasVolumeHeadings = /^## (?!#)/m.test(trimmed);
  // Check if we have ### chapter headings
  const hasChapterHeadings = /^### /m.test(trimmed);

  if (!hasVolumeHeadings && !hasChapterHeadings) {
    // Completely unparseable
    return {
      volumes: [],
      parseErrors: [trimmed],
    };
  }

  if (!hasVolumeHeadings && hasChapterHeadings) {
    // Short-novel format: no volumes, just chapters -> wrap in implicit volume
    const volume = parseVolumeBlock(trimmed, "");
    return {
      volumes: [volume],
      parseErrors: [],
    };
  }

  // Split by ## headings into volume blocks
  const volumeParts = trimmed.split(/(?=^## (?!#))/m);
  const volumes: ParsedVolume[] = [];
  const parseErrors: string[] = [];

  for (const part of volumeParts) {
    const cleaned = part.trim();
    if (!cleaned) continue;

    if (cleaned.match(/^## (?!#)/)) {
      // Extract volume title from first line
      const firstLineEnd = cleaned.indexOf("\n");
      const titleLine =
        firstLineEnd === -1 ? cleaned : cleaned.substring(0, firstLineEnd);
      const title = titleLine.replace(/^##\s*/, "").trim();
      const body = firstLineEnd === -1 ? "" : cleaned.substring(firstLineEnd);

      volumes.push(parseVolumeBlock(body, title));
    } else {
      // Content before first ## heading that isn't parseable
      parseErrors.push(cleaned);
    }
  }

  return { volumes, parseErrors };
}
