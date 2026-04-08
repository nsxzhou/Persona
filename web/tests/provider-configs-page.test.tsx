import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { ProviderConfigsPageView } from "@/components/provider-configs-page-view";


test("provider configs page opens create dialog and triggers connection test", () => {
  const onOpenCreate = vi.fn();
  const onTest = vi.fn();

  render(
    <ProviderConfigsPageView
      providers={[
        {
          id: "provider-1",
          label: "Primary Gateway",
          base_url: "https://api.openai.com/v1",
          default_model: "gpt-4.1-mini",
          api_key_hint: "****1234",
          is_enabled: true,
          last_test_status: "success",
          last_test_error: null,
          last_tested_at: "2026-04-07T12:00:00Z",
        },
      ]}
      onOpenCreate={onOpenCreate}
      onTest={onTest}
    />,
  );

  fireEvent.click(screen.getByRole("button", { name: "新增配置" }));
  fireEvent.click(screen.getByRole("button", { name: "测试连接" }));

  expect(onOpenCreate).toHaveBeenCalled();
  expect(onTest).toHaveBeenCalledWith("provider-1");
  expect(screen.getByText("****1234")).toBeInTheDocument();
});

