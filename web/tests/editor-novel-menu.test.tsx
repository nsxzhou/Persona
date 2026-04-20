import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { EditorNovelMenu } from "@/components/editor-novel-menu";

describe("EditorNovelMenu", () => {
  test("renders novel title and all bible tabs with correct tab query", () => {
    render(<EditorNovelMenu projectId="proj-42" projectName="血色长安" />);

    expect(screen.getByText("血色长安")).toBeInTheDocument();

    const expected: Array<[string, string]> = [
      ["简介", "description"],
      ["世界观设定", "world_building"],
      ["角色卡", "characters"],
      ["总纲", "outline_master"],
      ["分卷与章节细纲", "outline_detail"],
      ["运行时状态", "runtime_state"],
      ["伏笔与线索追踪", "runtime_threads"],
    ];

    for (const [label, tab] of expected) {
      const link = screen.getByRole("link", { name: new RegExp(label) });
      expect(link).toHaveAttribute("href", `/projects/proj-42?tab=${tab}`);
    }
  });

  test("includes back-to-workbench and all-projects footer links", () => {
    render(<EditorNovelMenu projectId="proj-42" projectName="血色长安" />);
    expect(screen.getByRole("link", { name: /返回项目工作台/ })).toHaveAttribute(
      "href",
      "/projects/proj-42",
    );
    expect(screen.getByRole("link", { name: /所有项目/ })).toHaveAttribute(
      "href",
      "/projects",
    );
  });
});
