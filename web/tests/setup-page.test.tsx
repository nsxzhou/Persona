import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import SetupPage from "@/app/setup/page";
import { SetupPageClient } from "@/components/route-guards";

const redirectMock = vi.hoisted(() => vi.fn());
const replaceMock = vi.hoisted(() => vi.fn());
const getServerApiMock = vi.hoisted(() => vi.fn());
const getServerCurrentUserMock = vi.hoisted(() => vi.fn());
const setupMock = vi.hoisted(() => vi.fn());
const toastSuccessMock = vi.hoisted(() => vi.fn());
const toastErrorMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/lib/server-api", () => ({
  getServerApi: getServerApiMock,
  getServerCurrentUser: getServerCurrentUserMock,
}));

vi.mock("@/lib/api", () => ({
  api: {
    setup: setupMock,
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: toastSuccessMock,
    error: toastErrorMock,
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

test("server setup page redirects to login when already initialized but not logged in", async () => {
  getServerApiMock.mockResolvedValueOnce({
    getSetupStatus: vi.fn().mockResolvedValueOnce({ initialized: true }),
  });
  getServerCurrentUserMock.mockResolvedValueOnce(null);

  await SetupPage();

  expect(redirectMock).toHaveBeenCalledWith("/login");
});

test("server setup page redirects to projects when already initialized and logged in", async () => {
  getServerApiMock.mockResolvedValueOnce({
    getSetupStatus: vi.fn().mockResolvedValueOnce({ initialized: true }),
  });
  getServerCurrentUserMock.mockResolvedValueOnce({
    id: "user-1",
    username: "persona-admin",
    created_at: "2026-04-10T00:00:00Z",
  });

  await SetupPage();

  expect(redirectMock).toHaveBeenCalledWith("/projects");
});

test("setup client submits admin and first provider values then jumps to projects", async () => {
  setupMock.mockResolvedValueOnce({
    user: {
      id: "user-1",
      username: "persona-admin",
      created_at: "2026-04-10T00:00:00Z",
    },
    provider: {
      id: "provider-1",
      label: "Primary Gateway",
      base_url: "https://api.openai.com/v1",
      default_model: "gpt-4.1-mini",
      api_key_hint: "****9876",
      is_enabled: true,
      last_test_status: null,
      last_test_error: null,
      last_tested_at: null,
    },
  });

  const queryClient = new QueryClient();
  const invalidateQueriesSpy = vi.spyOn(queryClient, "invalidateQueries");

  render(
    <QueryClientProvider client={queryClient}>
      <SetupPageClient />
    </QueryClientProvider>,
  );

  fireEvent.change(screen.getByLabelText("管理员账号"), {
    target: { value: "persona-admin" },
  });
  fireEvent.change(screen.getByLabelText("登录密码"), {
    target: { value: "super-secret-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "下一步" }));

  fireEvent.change(await screen.findByLabelText("名称"), {
    target: { value: "Primary Gateway" },
  });
  fireEvent.change(screen.getByLabelText("Base URL"), {
    target: { value: "https://api.openai.com/v1" },
  });
  fireEvent.change(screen.getByLabelText("API Key"), {
    target: { value: "sk-live-9876" },
  });
  fireEvent.change(screen.getByLabelText("默认模型"), {
    target: { value: "gpt-4.1-mini" },
  });
  fireEvent.click(screen.getByRole("button", { name: "完成初始化" }));

  await waitFor(() => {
    expect(setupMock).toHaveBeenCalledWith({
      username: "persona-admin",
      password: "super-secret-password",
      provider: {
        label: "Primary Gateway",
        base_url: "https://api.openai.com/v1",
        api_key: "sk-live-9876",
        default_model: "gpt-4.1-mini",
        is_enabled: true,
      },
    });
  });

  await waitFor(() => {
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ["setup-status"] });
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ["current-user"] });
    expect(replaceMock).toHaveBeenCalledWith("/projects");
    expect(toastSuccessMock).toHaveBeenCalledWith("系统初始化成功");
  });
});
