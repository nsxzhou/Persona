import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, test, vi } from "vitest";

import ModelConfigsPage from "@/app/(workspace)/settings/models/page";

vi.mock("sonner", () => {
  return {
    toast: {
      loading: vi.fn(() => "toast-id"),
      success: vi.fn(),
      error: vi.fn(),
    },
  };
});

vi.mock("@/lib/api", () => {
  return {
    api: {
      getProviderConfigs: vi.fn(async () => [
        {
          id: "provider-1",
          label: "Primary Gateway",
          base_url: "https://api.openai.com/v1",
          default_model: "gpt-4.1-mini",
          api_key_hint: "****1234",
          is_enabled: true,
          last_test_status: null,
          last_test_error: null,
          last_tested_at: null,
        },
      ]),
      testProviderConfig: vi.fn(async () => ({ status: "success", message: "连接成功" })),
      deleteProviderConfig: vi.fn(),
      updateProviderConfig: vi.fn(),
      createProviderConfig: vi.fn(),
    },
  };
});

test("clicking test connection shows immediate loading feedback", async () => {
  const queryClient = new QueryClient();

  render(
    <QueryClientProvider client={queryClient}>
      <ModelConfigsPage />
    </QueryClientProvider>
  );

  const button = await screen.findByRole("button", { name: "测试连接" });
  fireEvent.click(button);

  const { toast } = await import("sonner");
  await waitFor(() => expect(toast.loading).toHaveBeenCalled());
});

