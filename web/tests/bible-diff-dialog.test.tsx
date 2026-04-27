import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { BibleDiffDialog } from "@/components/bible-diff-dialog";

describe("BibleDiffDialog", () => {
  function renderDialog() {
    const onAccept = vi.fn();
    const onDismiss = vi.fn();
    const onRetry = vi.fn();

    render(
      <BibleDiffDialog
        open
        currentCharactersStatus={"旧角色状态"}
        proposedCharactersStatus={"旧角色状态\n新角色状态"}
        currentState={"旧状态\n保留"}
        proposedState={"旧状态\n新状态"}
        currentThreads={"旧线索\n保留"}
        proposedThreads={"旧线索\n新线索"}
        source="manual"
        onAccept={onAccept}
        onDismiss={onDismiss}
        onRetry={onRetry}
      />,
    );

    return { onAccept, onDismiss, onRetry };
  }

  test("opens regenerate feedback dialog and forwards feedback to onRetry", async () => {
    const { onRetry } = renderDialog();
    fireEvent.click(screen.getByRole("button", { name: "重新生成" }));

    const textarea = await screen.findByLabelText("本次生成的意见（可选）");
    fireEvent.change(textarea, { target: { value: "  更精简  " } });

    const regenerateButtons = screen.getAllByRole("button", { name: "重新生成" });
    fireEvent.click(regenerateButtons[regenerateButtons.length - 1]);
    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(onRetry).toHaveBeenCalledWith("更精简");
  });

  test("only changes mode hides unchanged lines instead of collapsing them", async () => {
    renderDialog();

    fireEvent.click(screen.getByRole("button", { name: "运行时状态" }));
    await waitFor(() => {
      expect(screen.getAllByText("旧状态").length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getByRole("switch"));

    expect(screen.queryByText("旧状态")).toBeNull();
    expect(screen.queryByText(/展开 .* 行未变更/)).toBeNull();
    expect(screen.getByText("新状态")).toBeInTheDocument();
  });
});
