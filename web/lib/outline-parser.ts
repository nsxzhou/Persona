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
  bodyMarkdown: string;
  chapters: ParsedChapter[];
  startOffset?: number;
  endOffset?: number;
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

const VOLUME_HEADING_RE = /^## (?!#)(.+)$/gm;
const CHAPTER_HEADING_RE = /^###\s+第\s*(?:\d+|[一二三四五六七八九十百千万零〇两]+)\s*章.*$/m;
const CHAPTER_SPLIT_RE = /(?=^###\s+第\s*(?:\d+|[一二三四五六七八九十百千万零〇两]+)\s*章.*$)/m;

function hasChapterHeading(text: string): boolean {
  return CHAPTER_HEADING_RE.test(text);
}

function isIgnorableSectionTitle(title: string): boolean {
  return title.replace(/\s+/g, "").includes("闭环验证");
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

function parseVolumeBlock(
  block: string,
  title: string,
  startOffset?: number,
  endOffset?: number,
): ParsedVolume {
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

  const firstChapterIndex = block.search(CHAPTER_HEADING_RE);
  const bodyMarkdown =
    firstChapterIndex === -1
      ? block.trim()
      : block.substring(0, firstChapterIndex).trim();
  const chapterMarkdown =
    firstChapterIndex === -1 ? "" : block.substring(firstChapterIndex);

  // Split into chapter blocks by real chapter headings only.
  const chapterBlocks: string[] = [];
  const chapterSplitParts = chapterMarkdown.split(CHAPTER_SPLIT_RE);

  for (const part of chapterSplitParts) {
    if (hasChapterHeading(part)) {
      chapterBlocks.push(part.trimEnd());
    }
  }

  const chapters = chapterBlocks.map(parseChapter);

  return { title, meta, bodyMarkdown, chapters, startOffset, endOffset };
}

export function parseOutline(markdown: string): ParsedOutline {
  if (markdown.trim() === "") {
    return { volumes: [], parseErrors: [] };
  }

  VOLUME_HEADING_RE.lastIndex = 0;
  const volumeMatches = [...markdown.matchAll(VOLUME_HEADING_RE)].map((match) => ({
    start: match.index ?? 0,
    end: (match.index ?? 0) + match[0].length,
    title: match[1].trim(),
  }));
  const hasChapterHeadings = hasChapterHeading(markdown);

  if (volumeMatches.length === 0 && !hasChapterHeadings) {
    // Completely unparseable
    return {
      volumes: [],
      parseErrors: [markdown.trim()],
    };
  }

  if (volumeMatches.length === 0 && hasChapterHeadings) {
    // Short-novel format: no volumes, just chapters -> wrap in implicit volume
    const volume = parseVolumeBlock(markdown, "", 0, markdown.length);
    return {
      volumes: [volume],
      parseErrors: [],
    };
  }

  const volumes: ParsedVolume[] = [];

  for (let i = 0; i < volumeMatches.length; i += 1) {
    const current = volumeMatches[i];
    const next = volumeMatches[i + 1];
    const blockEnd = next ? next.start : markdown.length;
    const body = markdown.substring(current.end, blockEnd);

    if (isIgnorableSectionTitle(current.title) && !hasChapterHeading(body)) {
      continue;
    }

    volumes.push(parseVolumeBlock(body, current.title, current.start, blockEnd));
  }

  if (volumes.length === 0) {
    return {
      volumes: [],
      parseErrors: [markdown.trim()],
    };
  }

  return { volumes, parseErrors: [] };
}

function renderVolumeWithChapters(volume: ParsedVolume, generatedChapters: string) {
  const parts = volume.title ? [`## ${volume.title}`] : [];
  const bodyMarkdown = volume.bodyMarkdown.trim();
  const normalizedChapters = generatedChapters.trim();

  if (bodyMarkdown) parts.push(bodyMarkdown);
  if (normalizedChapters) parts.push(normalizedChapters);

  return parts.join("\n\n").trim();
}

export function replaceVolumeChapters(
  value: string,
  volumeIndex: number,
  generatedChapters: string,
) {
  const parsed = parseOutline(value);
  const target = parsed.volumes[volumeIndex];
  if (!target) return value;

  const replacement = renderVolumeWithChapters(target, generatedChapters);

  if (target.startOffset !== undefined && target.endOffset !== undefined) {
    const before = value.substring(0, target.startOffset);
    const after = value.substring(target.endOffset);
    const separator = after.trim() ? "\n\n" : "";
    return `${before}${replacement}${separator}${after.replace(/^\n+/, "")}`.trim();
  }

  const lines: string[] = [];

  parsed.volumes.forEach((volume, index) => {
    if (index === volumeIndex) {
      lines.push(renderVolumeWithChapters(volume, generatedChapters));
      lines.push("");
      return;
    }

    lines.push(renderVolumeWithChapters(volume, volume.chapters.map((chapter) => chapter.rawMarkdown).join("\n\n")));
    lines.push("");
  });

  return lines.join("\n").trim();
}
