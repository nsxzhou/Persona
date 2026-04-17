import { describe, expect, test } from "vitest";

import {
  computeLineDiff,
  groupDiffBlocks,
  summarizeDiff,
} from "@/lib/diff-utils";

describe("computeLineDiff", () => {
  test("marks only changed lines, keeps unchanged lines intact", () => {
    const current = "a\nb\nc";
    const proposed = "a\nB\nc";
    const diff = computeLineDiff(current, proposed);
    expect(diff.map((line) => line.type)).toEqual([
      "unchanged",
      "removed",
      "added",
      "unchanged",
    ]);
    expect(diff.map((line) => line.text)).toEqual(["a", "b", "B", "c"]);
  });

  test("handles empty current (pure addition)", () => {
    const diff = computeLineDiff("", "new\nline");
    expect(summarizeDiff(diff)).toEqual({ added: 2, removed: 0, unchanged: 0 });
  });

  test("handles empty proposed (pure deletion)", () => {
    const diff = computeLineDiff("a\nb", "");
    expect(summarizeDiff(diff)).toEqual({ added: 0, removed: 2, unchanged: 0 });
  });
});

describe("groupDiffBlocks", () => {
  const diff = computeLineDiff(
    "l1\nl2\nl3\nl4\nl5\nl6\nl7\nl8",
    "l1\nl2\nl3\nxx\nl5\nl6\nl7\nl8",
  );

  test("returns untouched blocks when collapseUnchanged is false", () => {
    const blocks = groupDiffBlocks(diff);
    expect(blocks.length).toBeGreaterThan(1);
    expect(blocks.some((block) => block.type === "unchanged-collapsed")).toBe(false);
  });

  test("collapses long unchanged runs when requested", () => {
    const blocks = groupDiffBlocks(diff, { collapseUnchanged: true, contextLines: 1 });
    const collapsed = blocks.find((block) => block.type === "unchanged-collapsed");
    expect(collapsed).toBeDefined();
    expect(collapsed?.collapsedCount).toBeGreaterThan(0);
  });
});
