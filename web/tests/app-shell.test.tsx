import { render, screen } from "@testing-library/react";

import { AppShell } from "@/components/app-shell";


test("app shell renders left navigation items", () => {
  render(
    <AppShell>
      <div>content</div>
    </AppShell>,
  );

  expect(screen.getByText("项目")).toBeInTheDocument();
  expect(screen.getByText("模型配置")).toBeInTheDocument();
  expect(screen.getByText("风格实验室")).toBeInTheDocument();
  expect(screen.getByText("账户")).toBeInTheDocument();
});
