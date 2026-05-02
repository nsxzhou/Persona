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
const CHAPTER_REF_RE = /第\s*(\d+|[一二三四五六七八九十百千万零〇两]+)\s*(?:[-~－–—至到]\s*(\d+|[一二三四五六七八九十百千万零〇两]+))?\s*章/;

type H3Section = {
  title: string;
  start: number;
  end: number;
  body: string;
};

type ChapterReference = {
  numbers: number[];
  matchEnd: number;
};

type FallbackChapterDraft = ParsedChapter & {
  chapterNumber: number;
};

function hasChapterHeading(text: string): boolean {
  return CHAPTER_HEADING_RE.test(text);
}

export function hasStandardChapterHeadings(text: string): boolean {
  return hasChapterHeading(text);
}

function isIgnorableSectionTitle(title: string): boolean {
  const normalized = title.replace(/\s+/g, "");
  return ["闭环验证", "全篇爽点密度表"].some((keyword) => normalized.includes(keyword));
}

function parseChineseNumber(value: string): number | null {
  const digits: Record<string, number> = {
    零: 0,
    〇: 0,
    一: 1,
    二: 2,
    两: 2,
    三: 3,
    四: 4,
    五: 5,
    六: 6,
    七: 7,
    八: 8,
    九: 9,
  };
  const units: Record<string, number> = {
    十: 10,
    百: 100,
    千: 1000,
    万: 10000,
  };

  let total = 0;
  let section = 0;
  let number = 0;
  let consumed = false;

  for (const char of value) {
    if (char in digits) {
      number = digits[char];
      consumed = true;
      continue;
    }
    const unit = units[char];
    if (!unit) return null;
    consumed = true;
    if (unit === 10000) {
      total += (section + number || 1) * unit;
      section = 0;
      number = 0;
    } else {
      section += (number || 1) * unit;
      number = 0;
    }
  }

  const result = total + section + number;
  return consumed && result > 0 ? result : null;
}

function parseChapterNumber(value: string): number | null {
  if (/^\d+$/.test(value)) return Number.parseInt(value, 10);
  return parseChineseNumber(value);
}

function expandChapterNumbers(start: number, end: number | null): number[] {
  if (!Number.isFinite(start) || start <= 0) return [];
  if (end === null || end < start || end - start > 100) return [start];
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}

function parseChapterReference(text: string): ChapterReference | null {
  const match = text.match(CHAPTER_REF_RE);
  if (!match) return null;
  const start = parseChapterNumber(match[1]);
  if (start === null) return null;
  const end = match[2] ? parseChapterNumber(match[2]) : null;
  return {
    numbers: expandChapterNumbers(start, end),
    matchEnd: (match.index ?? 0) + match[0].length,
  };
}

function cleanInlineText(value: string): string {
  return value
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/\*\*/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function extractH3Sections(block: string): H3Section[] {
  const matches = [...block.matchAll(/^###\s+(.+)$/gm)];
  return matches.map((match, index) => {
    const start = match.index ?? 0;
    const end = matches[index + 1]?.index ?? block.length;
    const bodyStart = start + match[0].length;
    return {
      title: match[1].trim(),
      start,
      end,
      body: block.substring(bodyStart, end).trim(),
    };
  });
}

function isFallbackChapterSection(title: string): boolean {
  const normalized = title.replace(/\s+/g, "");
  return normalized.includes("节奏设计") || normalized.includes("主要节奏");
}

function isFallbackHookSection(title: string): boolean {
  return title.replace(/\s+/g, "").includes("章末");
}

function hasFallbackChapterSections(text: string): boolean {
  return extractH3Sections(text).some((section) => isFallbackChapterSection(section.title));
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map(cleanInlineText);
}

function isTableSeparatorRow(cells: string[]): boolean {
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")));
}

function buildFallbackChapter(
  chapterNumber: number,
  summary: string,
  hook: string,
): FallbackChapterDraft {
  const normalizedSummary = cleanInlineText(summary);
  const normalizedHook = cleanInlineText(hook);
  const title = normalizedSummary ? `第${chapterNumber}章：${normalizedSummary}` : `第${chapterNumber}章`;
  const rawParts = [`### ${title}`];
  if (normalizedSummary) rawParts.push(`- **核心事件**：${normalizedSummary}`);
  if (normalizedHook) rawParts.push(`- **章末钩子**：${normalizedHook}`);

  return {
    chapterNumber,
    title,
    coreEvent: normalizedSummary,
    emotionArc: "",
    chapterHook: normalizedHook,
    rawMarkdown: rawParts.join("\n"),
  };
}

function extractChapterHooks(block: string): Map<number, string> {
  const hooks = new Map<number, string>();
  for (const section of extractH3Sections(block)) {
    if (!isFallbackHookSection(section.title)) continue;
    for (const line of section.body.split("\n")) {
      const item = line.match(/^\s*[-*+]\s+(.+)$/);
      if (!item) continue;
      const ref = parseChapterReference(item[1]);
      if (!ref) continue;
      const hook = cleanInlineText(
        item[1]
          .slice(ref.matchEnd)
          .replace(/^\s*(?:结尾)?\s*[：:，,、\-—]\s*/, ""),
      );
      if (!hook) continue;
      for (const chapterNumber of ref.numbers) {
        hooks.set(chapterNumber, hook);
      }
    }
  }
  return hooks;
}

function parseFallbackTableChapters(
  sectionBody: string,
  hooks: Map<number, string>,
): FallbackChapterDraft[] {
  const rows = sectionBody
    .split("\n")
    .filter((line) => line.trim().startsWith("|") && line.includes("|"))
    .map(splitTableRow)
    .filter((cells) => cells.some(Boolean));
  const headerIndex = rows.findIndex((cells) => cells.some((cell) => cell.includes("章号")));
  if (headerIndex === -1) return [];

  const header = rows[headerIndex];
  const chapterColumn = header.findIndex((cell) => cell.includes("章号"));
  const contentColumn = header.findIndex((cell, index) => index !== chapterColumn && /内容|事件|剧情/.test(cell));
  const hookColumn = header.findIndex((cell) => /追读|驱动|钩子|悬念/.test(cell));
  const chapters: FallbackChapterDraft[] = [];

  for (const row of rows.slice(headerIndex + 1)) {
    if (isTableSeparatorRow(row)) continue;
    const chapterCell = row[chapterColumn] ?? row.find((cell) => parseChapterReference(cell)) ?? "";
    const ref = parseChapterReference(chapterCell);
    if (!ref) continue;

    const summary =
      contentColumn >= 0
        ? row[contentColumn]
        : row.filter((_, index) => index !== chapterColumn && index !== hookColumn).join(" ");
    const rowHook = hookColumn >= 0 ? row[hookColumn] : "";
    for (const chapterNumber of ref.numbers) {
      chapters.push(buildFallbackChapter(chapterNumber, summary, hooks.get(chapterNumber) ?? rowHook));
    }
  }

  return chapters;
}

function parseFallbackListChapters(
  sectionBody: string,
  hooks: Map<number, string>,
): FallbackChapterDraft[] {
  const chapters: FallbackChapterDraft[] = [];
  for (const line of sectionBody.split("\n")) {
    const item = line.match(/^\s*[-*+]\s+(.+)$/);
    if (!item) continue;
    const ref = parseChapterReference(item[1]);
    if (!ref) continue;
    const summary = cleanInlineText(
      item[1]
        .slice(ref.matchEnd)
        .replace(/^\s*[：:，,、\-—]\s*/, ""),
    );
    if (!summary) continue;
    for (const chapterNumber of ref.numbers) {
      chapters.push(buildFallbackChapter(chapterNumber, summary, hooks.get(chapterNumber) ?? ""));
    }
  }
  return chapters;
}

function parseFallbackChapters(block: string): ParsedChapter[] {
  const hooks = extractChapterHooks(block);
  const chapters: ParsedChapter[] = [];
  const seenChapterNumbers = new Set<number>();

  for (const section of extractH3Sections(block)) {
    if (!isFallbackChapterSection(section.title)) continue;
    const drafts = [
      ...parseFallbackTableChapters(section.body, hooks),
      ...parseFallbackListChapters(section.body, hooks),
    ];
    for (const draft of drafts) {
      if (seenChapterNumbers.has(draft.chapterNumber)) continue;
      seenChapterNumbers.add(draft.chapterNumber);
      const { chapterNumber: _chapterNumber, ...chapter } = draft;
      chapters.push(chapter);
    }
  }

  return chapters;
}

function removeFallbackChapterSections(block: string): string {
  const sections = extractH3Sections(block).filter(
    (section) => isFallbackChapterSection(section.title) || isFallbackHookSection(section.title),
  );
  if (sections.length === 0) return block.trim();

  let result = "";
  let cursor = 0;
  for (const section of sections) {
    result += block.substring(cursor, section.start);
    cursor = section.end;
  }
  result += block.substring(cursor);
  return result.replace(/\n{3,}/g, "\n\n").trim();
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
  const fallbackChapters = chapters.length === 0 ? parseFallbackChapters(block) : [];
  const finalBodyMarkdown = fallbackChapters.length > 0 ? removeFallbackChapterSections(block) : bodyMarkdown;

  return {
    title,
    meta,
    bodyMarkdown: finalBodyMarkdown,
    chapters: chapters.length > 0 ? chapters : fallbackChapters,
    startOffset,
    endOffset,
  };
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
  const hasFallbackHeadings = hasFallbackChapterSections(markdown);

  if (volumeMatches.length === 0 && !hasChapterHeadings && !hasFallbackHeadings) {
    // Completely unparseable
    return {
      volumes: [],
      parseErrors: [markdown.trim()],
    };
  }

  if (volumeMatches.length === 0 && (hasChapterHeadings || hasFallbackHeadings)) {
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

    if (isIgnorableSectionTitle(current.title) && !hasChapterHeading(body) && !hasFallbackChapterSections(body)) {
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
