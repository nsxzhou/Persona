import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { SetupPageView } from "@/components/setup-page-view";


test("setup page submits admin and first provider values", async () => {
  const onSubmit = vi.fn().mockResolvedValue(undefined);

  render(<SetupPageView onSubmit={onSubmit} submitting={false} />);

  fireEvent.change(screen.getByLabelText("管理员账号"), {
    target: { value: "persona-admin" },
  });
  fireEvent.change(screen.getByLabelText("登录密码"), {
    target: { value: "super-secret-password" },
  });
  fireEvent.change(screen.getByLabelText("Provider 名称"), {
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

  expect(onSubmit).toHaveBeenCalledWith({
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

