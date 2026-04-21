import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { AppShell } from "@/components/app-shell";

vi.mock("next/navigation", () => ({
  usePathname: () => "/projects",
}));

test("app shell renders plot lab navigation entry", () => {
  render(
    <AppShell>
      <div>content</div>
    </AppShell>,
  );

  expect(screen.getByText("情节实验室")).toBeInTheDocument();
});
