import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { RegenerateDialog } from "@/components/regenerate-dialog";

describe("RegenerateDialog", () => {
  function renderDialog(overrides: Partial<React.ComponentProps<typeof RegenerateDialog>> = {}) {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();

    render(
      <RegenerateDialog
        open
        title="重新生成节拍"
        onCancel={onCancel}
        onConfirm={onConfirm}
        {...overrides}
      />,
    );

    return { onCancel, onConfirm };
  }

  test("submits an empty trimmed feedback when user clicks regenerate without typing", () => {
    const { onConfirm } = renderDialog();
    fireEvent.click(screen.getByRole("button", { name: "重新生成" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith("");
  });

  test("submits the trimmed feedback text when provided", () => {
    const { onConfirm } = renderDialog();
    const textarea = screen.getByLabelText("本次生成的意见（可选）");
    fireEvent.change(textarea, { target: { value: "  节奏更快  " } });
    fireEvent.click(screen.getByRole("button", { name: "重新生成" }));
    expect(onConfirm).toHaveBeenCalledWith("节奏更快");
  });

  test("disables the form and labels the submit button while busy", () => {
    renderDialog({ busy: true });

    const submit = screen.getByRole("button", { name: "生成中…" });
    expect(submit).toBeDisabled();
    expect(screen.getByRole("button", { name: "取消" })).toBeDisabled();
    expect(screen.getByLabelText("本次生成的意见（可选）")).toBeDisabled();
  });

  test("does not call onConfirm when the regenerate button is busy", () => {
    const { onConfirm } = renderDialog({ busy: true });
    fireEvent.click(screen.getByRole("button", { name: "生成中…" }));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  test("calls onCancel when the cancel button is clicked", () => {
    const { onCancel, onConfirm } = renderDialog();
    fireEvent.click(screen.getByRole("button", { name: "取消" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
