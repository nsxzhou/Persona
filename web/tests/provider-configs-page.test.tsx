import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { SetupPageView } from "@/components/setup-page-view";
import { ProviderConfigFormDialog } from "@/components/provider-config-form-dialog";
import { ProviderConfigsPageView } from "@/components/provider-configs-page-view";

if (typeof globalThis.ResizeObserver === "undefined") {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverMock as typeof ResizeObserver;
}


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

test("setup page uses the shared provider default model", async () => {
  const onSubmit = vi.fn().mockResolvedValue(undefined);

  render(<SetupPageView onSubmit={onSubmit} submitting={false} />);

  fireEvent.change(screen.getByLabelText("管理员账号"), {
    target: { value: "persona-admin" },
  });
  fireEvent.change(screen.getByLabelText("登录密码"), {
    target: { value: "super-secret-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "下一步" }));

  expect(await screen.findByLabelText("默认模型")).toHaveValue("gpt-4.1-mini");
});

test("provider config dialog validates base url before submit", async () => {
  const onSubmit = vi.fn(async () => {});

  render(
    <ProviderConfigFormDialog
      open
      provider={null}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={onSubmit}
    />,
  );

  fireEvent.change(screen.getByLabelText("名称"), {
    target: { value: "Primary Gateway" },
  });
  fireEvent.change(screen.getByLabelText("Base URL"), {
    target: { value: "not-a-url" },
  });
  fireEvent.change(screen.getByLabelText("API Key"), {
    target: { value: "sk-live-1234" },
  });
  fireEvent.click(screen.getByRole("button", { name: "创建配置" }));

  await waitFor(() => {
    expect(onSubmit).not.toHaveBeenCalled();
  });
  expect(screen.getByText("需为有效 URL")).toBeInTheDocument();
});

test("settings models page is a server wrapper around the provider configs client container", async () => {
  vi.resetModules();
  vi.doMock("@/components/provider-configs-page-view", () => ({
    ProviderConfigsPageClient: () => <div>provider-configs-client-container</div>,
    ProviderConfigsPageView: () => null,
  }));

  const { default: ModelConfigsPage } = await import("@/app/(workspace)/settings/models/page");

  render(<ModelConfigsPage />);

  expect(screen.getByText("provider-configs-client-container")).toBeInTheDocument();
});
