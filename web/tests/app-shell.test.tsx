import { render, screen } from "@testing-library/react";

import { AppShell } from "@/components/app-shell";


test("app shell renders left navigation items", () => {
  render(
    <AppShell>
      <div>content</div>
    </AppShell>,
  );

  expect(screen.getByText("Projects")).toBeInTheDocument();
  expect(screen.getByText("Model Configs")).toBeInTheDocument();
  expect(screen.getByText("Style Lab")).toBeInTheDocument();
  expect(screen.getByText("Account")).toBeInTheDocument();
});
