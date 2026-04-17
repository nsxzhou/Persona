import { diffLines } from "diff";

export type DiffLineType = "added" | "removed" | "unchanged";

export interface DiffSegment {
  type: DiffLineType;
  text: string;
}

export interface DiffLine {
  type: DiffLineType;
  text: string;
}

export interface DiffStats {
  added: number;
  removed: number;
  unchanged: number;
}

function splitLines(value: string): string[] {
  if (value === "") return [];
  const trimmed = value.endsWith("\n") ? value.slice(0, -1) : value;
  return trimmed.split("\n");
}

/**
 * Compute a line-level diff between `current` and `proposed`.
 * Each returned line carries exactly one of "added" / "removed" / "unchanged".
 * Trailing newline is ignored so lines align cleanly.
 */
export function computeLineDiff(current: string, proposed: string): DiffLine[] {
  const segments = diffLines(current, proposed);
  const result: DiffLine[] = [];
  for (const segment of segments) {
    const type: DiffLineType = segment.added
      ? "added"
      : segment.removed
        ? "removed"
        : "unchanged";
    for (const line of splitLines(segment.value)) {
      result.push({ type, text: line });
    }
  }
  return result;
}

/** Summary counts for a diff, useful for header badges. */
export function summarizeDiff(lines: DiffLine[]): DiffStats {
  const stats: DiffStats = { added: 0, removed: 0, unchanged: 0 };
  for (const line of lines) stats[line.type] += 1;
  return stats;
}

export interface DiffBlock {
  type: DiffLineType | "unchanged-collapsed";
  lines: DiffLine[];
  collapsedCount?: number;
}

/**
 * Group consecutive lines by change type. Pass `collapseUnchanged: true`
 * to fold long runs of unchanged lines into a single collapsible block.
 */
export function groupDiffBlocks(
  lines: DiffLine[],
  options: { collapseUnchanged?: boolean; contextLines?: number } = {},
): DiffBlock[] {
  const { collapseUnchanged = false, contextLines = 2 } = options;
  const blocks: DiffBlock[] = [];
  let current: DiffBlock | null = null;
  for (const line of lines) {
    if (!current || current.type !== line.type) {
      current = { type: line.type, lines: [line] };
      blocks.push(current);
    } else {
      current.lines.push(line);
    }
  }
  if (!collapseUnchanged) return blocks;

  const output: DiffBlock[] = [];
  blocks.forEach((block, index) => {
    if (block.type !== "unchanged") {
      output.push(block);
      return;
    }
    const isFirst = index === 0;
    const isLast = index === blocks.length - 1;
    const keepHead = isFirst ? 0 : Math.min(contextLines, block.lines.length);
    const keepTail = isLast ? 0 : Math.min(contextLines, block.lines.length);
    const total = block.lines.length;
    if (total <= keepHead + keepTail + 1) {
      output.push(block);
      return;
    }
    if (keepHead > 0) {
      output.push({ type: "unchanged", lines: block.lines.slice(0, keepHead) });
    }
    const hiddenCount = total - keepHead - keepTail;
    output.push({
      type: "unchanged-collapsed",
      lines: block.lines.slice(keepHead, total - keepTail),
      collapsedCount: hiddenCount,
    });
    if (keepTail > 0) {
      output.push({ type: "unchanged", lines: block.lines.slice(total - keepTail) });
    }
  });
  return output;
}
