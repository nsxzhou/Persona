import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

vi.mock("@/lib/server-api", () => ({
  getServerApi: vi.fn().mockResolvedValue({
    getProject: vi.fn().mockResolvedValue({
      id: "project-1",
      name: "反派攻略手册",
      description: "",
      status: "active",
      default_provider_id: "provider-1",
      default_model: "gpt-4.1-mini",
      style_profile_id: "style-1",
      inspiration: "",
      world_building: "",
      characters: "",
      outline_master: "",
      outline_detail: "",
      story_bible: "",
      content: "",
      length_preset: "short",
      archived_at: null,
      created_at: "2026-04-10T00:00:00Z",
      updated_at: "2026-04-10T00:00:00Z",
    }),
    getStyleProfile: vi.fn().mockResolvedValue({
      style_name: "娱乐春秋",
    }),
  }),
}));

vi.mock("@/components/zen-editor-view", () => ({
  ZenEditorView: (props: Record<string, unknown>) => (
    <div>
      <div>zen-editor-view</div>
      <div>{JSON.stringify(props.initialChapterSelection)}</div>
      <div>{String(props.initialIntent)}</div>
    </div>
  ),
}));

describe("ZenEditorPage", () => {
  test("passes chapter entry context from search params into the editor view", async () => {
    const ZenEditorPage = (await import("@/app/(workspace)/projects/[id]/editor/page")).default;

    render(
      await ZenEditorPage({
        params: Promise.resolve({ id: "project-1" }),
        searchParams: Promise.resolve({
          volumeIndex: "0",
          chapterIndex: "1",
          intent: "generate_beats",
        }),
      } as never),
    );

    expect(screen.getByText("zen-editor-view")).toBeInTheDocument();
    expect(screen.getByText('{"volumeIndex":0,"chapterIndex":1}')).toBeInTheDocument();
    expect(screen.getByText("generate_beats")).toBeInTheDocument();
  });
});
