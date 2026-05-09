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
        immersion_prompt_override_enabled: false,
        immersion_system_prompt_suffix: "",
        chat_test_system_prompt: "",
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
        immersion_prompt_override_enabled: false,
        immersion_system_prompt_suffix: "",
        chat_test_system_prompt: "",
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
        immersion_prompt_override_enabled: false,
        immersion_system_prompt_suffix: "",
        chat_test_system_prompt: "",
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
        immersion_prompt_override_enabled: false,
        immersion_system_prompt_suffix: "",
        chat_test_system_prompt: "",
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

test("provider prompt dialog saves override fields through update endpoint", async () => {
  apiMock.getProviderConfigs.mockResolvedValueOnce([
    {
      id: "provider-1",
      label: "Primary Gateway",
      base_url: "https://api.openai.com/v1",
      default_model: "gpt-4.1-mini",
      api_key_hint: "****1234",
      is_enabled: true,
      immersion_prompt_override_enabled: false,
      immersion_system_prompt_suffix: "",
      chat_test_system_prompt: "",
      last_test_status: null,
      last_test_error: null,
      last_tested_at: null,
    },
  ]);
  apiMock.updateProviderConfig.mockResolvedValueOnce({
    id: "provider-1",
    label: "Primary Gateway",
    base_url: "https://api.openai.com/v1",
    default_model: "gpt-4.1-mini",
    api_key_hint: "****1234",
    is_enabled: true,
    immersion_prompt_override_enabled: true,
    immersion_system_prompt_suffix: "Provider suffix",
    chat_test_system_prompt: "",
    last_test_status: null,
    last_test_error: null,
    last_tested_at: null,
  });

  renderPage();

  await screen.findByText("Primary Gateway");
  fireEvent.click(screen.getAllByRole("button", { name: "提示词" })[0]);
  fireEvent.click(await screen.findByLabelText("启用沉浸提示词追加"));
  fireEvent.change(screen.getByLabelText("沉浸模式 System Prompt 追加内容"), {
    target: { value: "Provider suffix" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存提示词" }));

  await waitFor(() => {
    expect(apiMock.updateProviderConfig).toHaveBeenCalledWith("provider-1", {
      immersion_prompt_override_enabled: true,
      immersion_system_prompt_suffix: "Provider suffix",
    });
  });
});

test("provider connection edit does not submit prompt override fields", async () => {
  apiMock.getProviderConfigs.mockResolvedValueOnce([
    {
      id: "provider-1",
      label: "Primary Gateway",
      base_url: "https://api.openai.com/v1",
      default_model: "gpt-4.1-mini",
      api_key_hint: "****1234",
      is_enabled: true,
      immersion_prompt_override_enabled: true,
      immersion_system_prompt_suffix: "Existing suffix",
      chat_test_system_prompt: "Saved test prompt",
      last_test_status: null,
      last_test_error: null,
      last_tested_at: null,
    },
  ]);
  apiMock.updateProviderConfig.mockResolvedValueOnce({
    id: "provider-1",
    label: "Primary Gateway Updated",
    base_url: "https://gateway.example.com/v1",
    default_model: "gpt-4.1-mini",
    api_key_hint: "****1234",
    is_enabled: true,
    immersion_prompt_override_enabled: true,
    immersion_system_prompt_suffix: "Existing suffix",
    chat_test_system_prompt: "Saved test prompt",
    last_test_status: null,
    last_test_error: null,
    last_tested_at: null,
  });

  renderPage();

  await screen.findByText("Primary Gateway");
  fireEvent.click(screen.getByRole("button", { name: "编辑" }));
  fireEvent.change(await screen.findByLabelText("名称"), {
    target: { value: "Primary Gateway Updated" },
  });
  fireEvent.change(screen.getByLabelText("Base URL"), {
    target: { value: "https://gateway.example.com/v1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

  await waitFor(() => {
    expect(apiMock.updateProviderConfig).toHaveBeenCalledWith("provider-1", {
      label: "Primary Gateway Updated",
      base_url: "https://gateway.example.com/v1",
      api_key: "",
      default_model: "gpt-4.1-mini",
      is_enabled: true,
    });
  });
});
