import { render, screen } from "@testing-library/react";

import { ProviderConfigsPageView } from "@/components/provider-configs-page-view";

test("provider configs page disables and marks the testing button while testing", () => {
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
      onOpenCreate={() => undefined}
      onTest={() => undefined}
      testingId="provider-1"
      testing={true}
    />
  );

  const button = screen.getByRole("button", { name: "测试中…" });
  expect(button).toBeDisabled();
});

