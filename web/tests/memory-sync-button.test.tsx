import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { MemorySyncButton, formatRelativeTime } from "@/components/memory-sync-button";
import { TooltipProvider } from "@/components/ui/tooltip";

function renderButton(props: Partial<React.ComponentProps<typeof MemorySyncButton>> = {}) {
  const merged: React.ComponentProps<typeof MemorySyncButton> = {
    snapshot: null,
    isChecking: false,
    disabled: false,
    onClick: vi.fn(),
    ...props,
  };
  return {
    ...render(
      <TooltipProvider>
        <MemorySyncButton {...merged} />
      </TooltipProvider>,
    ),
    props: merged,
  };
}

describe("MemorySyncButton", () => {
  test("renders '同步记忆' with no pill when snapshot is empty", () => {
    renderButton();
    expect(screen.getByRole("button", { name: /同步记忆/ })).toBeEnabled();
    expect(screen.queryByTestId("memory-sync-pill")).toBeNull();
  });

  test("renders '待确认' pill for pending_review", () => {
    renderButton({
      snapshot: {
        status: "pending_review",
        source: "auto",
        checkedAt: "2026-04-17T00:00:00Z",
        errorMessage: null,
      },
    });
    const pill = screen.getByTestId("memory-sync-pill");
    expect(pill).toHaveTextContent("待确认");
    expect(pill.className).toContain("bg-orange-500/15");
  });

  test("shows '分析中' pulsing pill when isChecking", () => {
    renderButton({ isChecking: true });
    const pill = screen.getByTestId("memory-sync-pill");
    expect(pill).toHaveTextContent("分析中");
    expect(pill.className).toContain("animate-pulse");
  });

  test("swaps button label to '重试同步' when status is failed", () => {
    renderButton({
      snapshot: {
        status: "failed",
        source: "manual",
        checkedAt: null,
        errorMessage: "timeout",
      },
    });
    expect(screen.getByRole("button", { name: /重试同步/ })).toBeInTheDocument();
  });

  test("renders '查看提议' for pending review", () => {
    renderButton({
      snapshot: {
        status: "pending_review",
        source: "manual",
        checkedAt: "2026-04-17T00:00:00Z",
        errorMessage: null,
      },
    });
    expect(screen.getByRole("button", { name: "查看提议" })).toBeInTheDocument();
  });

  test("renders '已是最新' and force rerun action for synced chapters", () => {
    const onForceRerun = vi.fn();
    renderButton({
      snapshot: {
        status: "synced",
        source: "manual",
        checkedAt: "2026-04-17T00:00:00Z",
        errorMessage: null,
      },
      onForceRerun,
    });
    expect(screen.getByRole("button", { name: "已是最新" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "强制重跑" }));
    expect(onForceRerun).toHaveBeenCalledTimes(1);
  });

  test("does not fire onClick when disabled", () => {
    const onClick = vi.fn();
    renderButton({ disabled: true, onClick });
    fireEvent.click(screen.getByRole("button", { name: /同步记忆/ }));
    expect(onClick).not.toHaveBeenCalled();
  });

  test("fires onClick when enabled", () => {
    const onClick = vi.fn();
    renderButton({ onClick });
    fireEvent.click(screen.getByRole("button", { name: /同步记忆/ }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("formatRelativeTime", () => {
  const now = new Date("2026-04-17T12:00:00Z");

  test("returns '刚刚' for very recent times", () => {
    expect(formatRelativeTime("2026-04-17T11:59:50Z", now)).toBe("刚刚");
  });

  test("returns minutes ago", () => {
    expect(formatRelativeTime("2026-04-17T11:30:00Z", now)).toBe("30 分钟前");
  });

  test("returns hours ago", () => {
    expect(formatRelativeTime("2026-04-17T06:00:00Z", now)).toBe("6 小时前");
  });

  test("returns null for missing input", () => {
    expect(formatRelativeTime(null)).toBeNull();
  });
});
