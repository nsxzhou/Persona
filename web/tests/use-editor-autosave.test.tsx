import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { toast } from "sonner";

import { useEditorAutosave } from "@/hooks/use-editor-autosave";

const apiMock = vi.hoisted(() => ({
  updateProjectChapter: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    updateProjectChapter: apiMock.updateProjectChapter,
  },
}));

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
  },
}));

describe("useEditorAutosave", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiMock.updateProjectChapter.mockReset();
    apiMock.updateProjectChapter.mockResolvedValue({
      id: "chapter-1",
      project_id: "project-1",
      volume_index: 0,
      chapter_index: 0,
      title: "第1章",
      content: "新的正文",
      word_count: 4,
    });
  });

  test("exposes saveNow and reports the saved chapter back to the caller", async () => {
    const onSaved = vi.fn();
    const { result } = renderHook(() =>
      useEditorAutosave("project-1", "chapter-1", "新的正文", "旧正文", false, onSaved),
    );

    await act(async () => {
      await result.current.saveNow("新的正文");
    });

    expect(apiMock.updateProjectChapter).toHaveBeenCalledWith(
      "project-1",
      "chapter-1",
      { content: "新的正文" },
    );
    expect(onSaved).toHaveBeenCalled();
  });

  test("flushPendingSave surfaces save failures instead of swallowing them", async () => {
    apiMock.updateProjectChapter.mockRejectedValueOnce(new Error("写入失败"));
    const { result, rerender } = renderHook(
      ({ currentContent, savedContent }) =>
        useEditorAutosave("project-1", "chapter-1", currentContent, savedContent, false),
      {
        initialProps: {
          currentContent: "新的正文",
          savedContent: "旧正文",
        },
      },
    );

    rerender({
      currentContent: "新的正文",
      savedContent: "新的正文",
    });

    await expect(result.current.flushPendingSave()).rejects.toThrow("写入失败");
    expect(toast.error).toHaveBeenCalledWith("自动保存失败");
  });
});
