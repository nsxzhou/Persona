import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";

import { ProviderConfigsPageClient } from "@/components/provider-configs-page-view";

const apiMock = vi.hoisted(() => ({
  getProviderConfigs: vi.fn(),
  deleteProviderConfig: vi.fn(),
  createProviderConfig: vi.fn(),
  updateProviderConfig: vi.fn(),
  testProviderConfig: vi.fn(),
}));

vi.mock("sonner", () => {
  return {
    toast: {
      success: vi.fn(),
      error: vi.fn(),
      loading: vi.fn(() => "toast-id"),
    },
  };
});

vi.mock("@/lib/api", () => {
  return {
    api: apiMock,
  };
});

function renderPage() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ProviderConfigsPageClient />
    </QueryClientProvider>,
  );
}

test("provider delete updates list immediately even if refetch returns stale snapshot", async () => {
  apiMock.getProviderConfigs
    .mockResolvedValueOnce([
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
      {
        id: "provider-2",
        label: "Backup Gateway",
        base_url: "https://api.openai.com/v1",
        default_model: "gpt-4.1-mini",
        api_key_hint: "****5678",
        is_enabled: true,
        last_test_status: null,
        last_test_error: null,
        last_tested_at: null,
      },
    ])
    .mockResolvedValueOnce([
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
      {
        id: "provider-2",
        label: "Backup Gateway",
        base_url: "https://api.openai.com/v1",
        default_model: "gpt-4.1-mini",
        api_key_hint: "****5678",
        is_enabled: true,
        last_test_status: null,
        last_test_error: null,
        last_tested_at: null,
      },
    ]);
  apiMock.deleteProviderConfig.mockResolvedValueOnce(undefined);

  renderPage();

  await screen.findByText("Primary Gateway");
  const deleteButtons = screen.getAllByRole("button", { name: "删除" });
  fireEvent.click(deleteButtons[0]);

  await waitFor(() => expect(apiMock.deleteProviderConfig).toHaveBeenCalledWith("provider-1"));
  await waitFor(() => expect(screen.queryByText("Primary Gateway")).not.toBeInTheDocument());
  expect(screen.getByText("Backup Gateway")).toBeInTheDocument();
});
