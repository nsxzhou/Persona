import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

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

test("server helper forwards cookie to setup status endpoint", async () => {
  vi.resetModules();
  vi.doMock("next/headers", () => ({
    cookies: vi.fn().mockResolvedValue({
      toString: () => "persona_session=token-1",
    }),
  }));
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ initialized: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

  const { getServerSetupStatus } = await import("@/lib/server-api");
  const result = await getServerSetupStatus();

  expect(result).toEqual({ initialized: true });
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledWith(
    "http://localhost:8000/api/v1/setup/status",
    expect.objectContaining({
      cache: "no-store",
      headers: expect.any(Headers),
    }),
  );
  const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
  expect(headers.get("cookie")).toBe("persona_session=token-1");
});

test("workspace layout redirects to setup when system is not initialized", async () => {
  vi.resetModules();
  const redirectMock = vi.fn();
  vi.doMock("next/navigation", () => ({
    redirect: redirectMock,
  }));
  vi.doMock("@/lib/server-api", () => ({
    getServerSetupStatus: vi.fn().mockResolvedValue({ initialized: false }),
    getServerCurrentUser: vi.fn(),
  }));

  const WorkspaceLayout = (await import("@/app/(workspace)/layout")).default;
  await WorkspaceLayout({ children: <div>content</div> });

  expect(redirectMock).toHaveBeenCalledWith("/setup");
});

test("workspace layout redirects to login when initialized but session missing", async () => {
  vi.resetModules();
  const redirectMock = vi.fn();
  vi.doMock("next/navigation", () => ({
    redirect: redirectMock,
  }));
  vi.doMock("@/lib/server-api", () => ({
    getServerSetupStatus: vi.fn().mockResolvedValue({ initialized: true }),
    getServerCurrentUser: vi.fn().mockResolvedValue(null),
  }));

  const WorkspaceLayout = (await import("@/app/(workspace)/layout")).default;
  await WorkspaceLayout({ children: <div>content</div> });

  expect(redirectMock).toHaveBeenCalledWith("/login");
});

test("workspace layout renders app shell for authenticated user", async () => {
  vi.resetModules();
  const redirectMock = vi.fn();
  vi.doMock("next/navigation", () => ({
    redirect: redirectMock,
  }));
  vi.doMock("@/lib/server-api", () => ({
    getServerSetupStatus: vi.fn().mockResolvedValue({ initialized: true }),
    getServerCurrentUser: vi.fn().mockResolvedValue({
      id: "user-1",
      username: "persona-admin",
      created_at: "2026-04-10T00:00:00Z",
    }),
  }));

  const WorkspaceLayout = (await import("@/app/(workspace)/layout")).default;
  const node = await WorkspaceLayout({ children: <div>workspace-content</div> });
  render(node);

  expect(screen.getByText("workspace-content")).toBeInTheDocument();
  expect(redirectMock).not.toHaveBeenCalled();
});
