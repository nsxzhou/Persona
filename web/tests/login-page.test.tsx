import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import LoginPage from "@/app/login/page";
import { LoginPageClient } from "@/components/route-guards";

const redirectMock = vi.hoisted(() => vi.fn());
const replaceMock = vi.hoisted(() => vi.fn());
const getServerSetupStatusMock = vi.hoisted(() => vi.fn());
const getServerCurrentUserMock = vi.hoisted(() => vi.fn());
const loginMock = vi.hoisted(() => vi.fn());
const toastSuccessMock = vi.hoisted(() => vi.fn());
const toastErrorMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/lib/server-api", () => ({
  getServerSetupStatus: getServerSetupStatusMock,
  getServerCurrentUser: getServerCurrentUserMock,
}));

vi.mock("@/lib/api", () => ({
  api: {
    login: loginMock,
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

test("server login page redirects to setup when system is not initialized", async () => {
  getServerSetupStatusMock.mockResolvedValueOnce({ initialized: false });

  await LoginPage();

  expect(redirectMock).toHaveBeenCalledWith("/setup");
});

test("server login page redirects to projects when already logged in", async () => {
  getServerSetupStatusMock.mockResolvedValueOnce({ initialized: true });
  getServerCurrentUserMock.mockResolvedValueOnce({
    id: "user-1",
    username: "persona-admin",
    created_at: "2026-04-10T00:00:00Z",
  });

  await LoginPage();

  expect(redirectMock).toHaveBeenCalledWith("/projects");
});

test("login client submits credentials and jumps to projects", async () => {
  loginMock.mockResolvedValueOnce({
    id: "user-1",
    username: "persona-admin",
    created_at: "2026-04-10T00:00:00Z",
  });

  const queryClient = new QueryClient();
  const invalidateQueriesSpy = vi.spyOn(queryClient, "invalidateQueries");

  render(
    <QueryClientProvider client={queryClient}>
      <LoginPageClient />
    </QueryClientProvider>,
  );

  fireEvent.change(screen.getByLabelText("管理员账号"), {
    target: { value: "persona-admin" },
  });
  fireEvent.change(screen.getByLabelText("登录密码"), {
    target: { value: "super-secret-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "进入工作台" }));

  await waitFor(() => {
    expect(loginMock).toHaveBeenCalledWith({
      username: "persona-admin",
      password: "super-secret-password",
    });
  });

  await waitFor(() => {
    expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ["current-user"] });
    expect(replaceMock).toHaveBeenCalledWith("/projects");
    expect(toastSuccessMock).toHaveBeenCalledWith("登录成功");
  });
});
