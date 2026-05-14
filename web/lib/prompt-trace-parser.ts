export type PromptTraceTable = Record<string, string>;

export type PromptTraceSegment = {
  id: string;
  title: string;
  kind: "message" | "output" | "section";
  metadata: PromptTraceTable;
  content: string;
  fallbackText?: string;
};

export type PromptTraceCall = {
  index: number;
  stage: string;
  mode: string;
  metadata: PromptTraceTable;
  segments: PromptTraceSegment[];
};

export type PromptTraceSummaryRow = {
  callIndex: string;
  stage: string;
  mode: string;
  model: string;
  inputChars: string;
  outputChars: string;
  truncated: string;
  error: string;
};

export type PromptTraceParseResult = {
  summary: PromptTraceTable;
  callSummary: PromptTraceSummaryRow[];
  calls: PromptTraceCall[];
};

type Section = {
  heading: string;
  body: string[];
};

const CALL_HEADING_RE = /^## Call (\d+) - (.+?) \/ (.+)$/;
const MESSAGE_HEADING_RE = /^### (System|User) message$/;
const KEY_VALUE_TABLE_HEADER = ["Field", "Value"];
const CALL_SUMMARY_TABLE_HEADER = [
  "#",
  "Stage",
  "Mode",
  "Model",
  "Input chars",
  "Output chars",
  "Truncated",
  "Error",
];

export function parsePromptTraceMarkdown(content: string): PromptTraceParseResult | null {
  const normalized = content.replace(/\r\n/g, "\n");
  const lines = normalized.split("\n");
  let cursor = 0;

  if (lines[cursor] !== "# Prompt Trace") return null;
  cursor += 1;
  cursor = skipBlank(lines, cursor);

  const summaryResult = parseKeyValueTable(lines, cursor);
  if (!summaryResult) return null;
  cursor = summaryResult.nextIndex;
  cursor = skipBlank(lines, cursor);

  const callSummary: PromptTraceSummaryRow[] = [];
  if (lines[cursor] === "## Call summary") {
    cursor += 1;
    cursor = skipBlank(lines, cursor);
    const tableResult = parseRowsTable(lines, cursor, CALL_SUMMARY_TABLE_HEADER);
    if (!tableResult) return null;
    cursor = tableResult.nextIndex;
    cursor = skipBlank(lines, cursor);

    for (const row of tableResult.rows) {
      const parsedRow = parseCallSummaryRow(row);
      if (!parsedRow) return null;
      callSummary.push(parsedRow);
    }
  }

  const calls: PromptTraceCall[] = [];
  while (cursor < lines.length) {
    cursor = skipBlank(lines, cursor);
    if (cursor >= lines.length) break;

    const callResult = parseCall(lines, cursor);
    if (!callResult) return null;
    calls.push(callResult.call);
    cursor = callResult.nextIndex;
  }

  return {
    summary: summaryResult.table,
    callSummary,
    calls,
  };
}

function parseCall(lines: string[], startIndex: number) {
  const headingMatch = lines[startIndex]?.match(CALL_HEADING_RE);
  if (!headingMatch) return null;

  const [, indexText, stage, mode] = headingMatch;
  let cursor = startIndex + 1;
  cursor = skipBlank(lines, cursor);

  const metadataResult = parseKeyValueTable(lines, cursor);
  if (!metadataResult) return null;
  cursor = metadataResult.nextIndex;
  cursor = skipBlank(lines, cursor);

  const sectionsResult = collectCallSections(lines, cursor);
  if (!sectionsResult) return null;
  const { sections } = sectionsResult;
  cursor = sectionsResult.nextIndex;

  const segments: PromptTraceSegment[] = [];
  for (const section of sections) {
    const segment = parseSegment(section, indexText, segments.length);
    if (!segment) return null;
    segments.push(segment);
  }

  if (!segments.some((segment) => segment.title === "Output excerpt")) return null;

  return {
    call: {
      index: Number(indexText),
      stage,
      mode,
      metadata: metadataResult.table,
      segments,
    },
    nextIndex: cursor,
  };
}

function parseSegment(section: Section, callIndex: string, sectionIndex: number): PromptTraceSegment | null {
  const headingText = section.heading.slice("### ".length);
  const metadata: PromptTraceTable = {};
  let cursor = skipBlank(section.body, 0);

  const isMessage = MESSAGE_HEADING_RE.test(section.heading);
  if (isMessage) {
    while (cursor < section.body.length && section.body[cursor].startsWith("- ")) {
      const metadataMatch = section.body[cursor].match(/^- ([^:]+): (.*)$/);
      if (!metadataMatch) return null;
      metadata[metadataMatch[1]] = stripInlineCode(metadataMatch[2]);
      cursor += 1;
    }
    cursor = skipBlank(section.body, cursor);
    const codeBlock = parseFencedCodeBlock(section.body, cursor);
    if (!codeBlock) return null;
    if (trimBlankLines(section.body.slice(codeBlock.nextIndex)).length > 0) return null;

    return {
      id: `call-${callIndex}-segment-${sectionIndex}`,
      title: headingText,
      kind: "message",
      metadata,
      content: codeBlock.content,
    };
  }

  if (headingText === "Output excerpt") {
    const codeBlock = parseFencedCodeBlock(section.body, cursor);
    if (codeBlock) {
      if (trimBlankLines(section.body.slice(codeBlock.nextIndex)).length > 0) return null;
      return {
        id: `call-${callIndex}-segment-${sectionIndex}`,
        title: headingText,
        kind: "output",
        metadata,
        content: codeBlock.content,
      };
    }

    const fallbackText = trimBlankLines(section.body).join("\n");
    if (!fallbackText) return null;

    return {
      id: `call-${callIndex}-segment-${sectionIndex}`,
      title: headingText,
      kind: "output",
      metadata,
      content: fallbackText,
      fallbackText,
    };
  }

  if (headingText === "Prompt Stack Manifest") {
    const content = trimBlankLines(section.body).join("\n");
    if (!content) return null;

    return {
      id: `call-${callIndex}-segment-${sectionIndex}`,
      title: headingText,
      kind: "section",
      metadata,
      content,
    };
  }

  return null;
}

function parseKeyValueTable(lines: string[], startIndex: number) {
  const table = parseRowsTable(lines, startIndex, KEY_VALUE_TABLE_HEADER);
  if (!table) return null;

  const result: PromptTraceTable = {};
  for (const row of table.rows) {
    if (row.length !== 2) return null;
    result[row[0]] = stripInlineCode(row[1]);
  }
  return { table: result, nextIndex: table.nextIndex };
}

function parseRowsTable(lines: string[], startIndex: number, expectedHeader: string[]) {
  if (!lines[startIndex]?.startsWith("|") || !lines[startIndex + 1]?.startsWith("|")) return null;
  if (!sameCells(splitTableRow(lines[startIndex]), expectedHeader)) return null;
  if (!isMarkdownSeparatorRow(lines[startIndex + 1], expectedHeader.length)) return null;

  let cursor = startIndex + 2;
  const rows: string[][] = [];
  while (cursor < lines.length && lines[cursor].startsWith("|")) {
    rows.push(splitTableRow(lines[cursor]));
    cursor += 1;
  }

  if (rows.length === 0) return null;
  return { rows, nextIndex: cursor };
}

function sameCells(actual: string[], expected: string[]) {
  return actual.length === expected.length && actual.every((cell, index) => cell === expected[index]);
}

function isMarkdownSeparatorRow(line: string, expectedCellCount: number) {
  const cells = splitTableRow(line);
  return (
    cells.length === expectedCellCount &&
    cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s/g, "")))
  );
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim();
  const body = trimmed.startsWith("|") ? trimmed.slice(1, trimmed.endsWith("|") ? -1 : undefined) : trimmed;
  const cells: string[] = [];
  let current = "";
  let escaping = false;

  for (const char of body) {
    if (escaping) {
      current += char === "|" ? "|" : `\\${char}`;
      escaping = false;
      continue;
    }
    if (char === "\\") {
      escaping = true;
      continue;
    }
    if (char === "|") {
      cells.push(current.trim());
      current = "";
      continue;
    }
    current += char;
  }
  if (escaping) current += "\\";
  cells.push(current.trim());
  return cells;
}

function parseCallSummaryRow(row: string[]): PromptTraceSummaryRow | null {
  if (row.length !== 8) return null;
  return {
    callIndex: row[0],
    stage: row[1],
    mode: row[2],
    model: row[3],
    inputChars: row[4],
    outputChars: row[5],
    truncated: row[6],
    error: row[7],
  };
}

function collectCallSections(lines: string[], startIndex: number): { sections: Section[]; nextIndex: number } | null {
  const sections: Section[] = [];
  let cursor = startIndex;

  while (cursor < lines.length && !isCallHeading(lines[cursor])) {
    const heading = lines[cursor];
    if (!isSegmentHeading(heading)) return null;
    cursor += 1;

    const body: string[] = [];
    let activeFence: string | null = null;
    while (cursor < lines.length) {
      const line = lines[cursor];
      if (!activeFence && (isSegmentHeading(line) || isCallHeading(line))) break;

      body.push(line);
      const fence = getStandaloneBacktickFence(line);
      if (fence) {
        activeFence = activeFence === fence ? null : activeFence ?? fence;
      }
      cursor += 1;
    }
    sections.push({ heading, body });
  }

  return { sections, nextIndex: cursor };
}

function isCallHeading(line: string | undefined) {
  return line?.startsWith("## Call ") ?? false;
}

function isSegmentHeading(line: string | undefined) {
  return line?.startsWith("### ") ?? false;
}

function parseFencedCodeBlock(lines: string[], startIndex: number): { content: string; nextIndex: number } | null {
  const fence = lines[startIndex];
  if (!getStandaloneBacktickFence(fence)) return null;

  const content: string[] = [];
  let cursor = startIndex + 1;
  while (cursor < lines.length) {
    if (lines[cursor] === fence) {
      return { content: content.join("\n"), nextIndex: cursor + 1 };
    }
    content.push(lines[cursor]);
    cursor += 1;
  }
  return null;
}

function getStandaloneBacktickFence(line: string | undefined): string | null {
  if (!line || !/^`{3,}$/.test(line)) return null;
  return line;
}

function skipBlank(lines: string[], startIndex: number) {
  let cursor = startIndex;
  while (cursor < lines.length && lines[cursor] === "") cursor += 1;
  return cursor;
}

function stripInlineCode(value: string) {
  return value.startsWith("`") && value.endsWith("`") && value.length >= 2
    ? value.slice(1, -1)
    : value;
}

function trimBlankLines(lines: string[]) {
  let start = 0;
  let end = lines.length;
  while (start < end && lines[start] === "") start += 1;
  while (end > start && lines[end - 1] === "") end -= 1;
  return lines.slice(start, end);
}
