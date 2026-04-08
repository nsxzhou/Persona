import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { LoginPageView } from "@/components/login-page-view";


test("login page submits username and password", async () => {
  const onSubmit = vi.fn().mockResolvedValue(undefined);

  render(<LoginPageView onSubmit={onSubmit} submitting={false} />);

  fireEvent.change(screen.getByLabelText("管理员账号"), {
    target: { value: "persona-admin" },
  });
  fireEvent.change(screen.getByLabelText("登录密码"), {
    target: { value: "super-secret-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "进入工作台" }));

  expect(onSubmit).toHaveBeenCalledWith({
    username: "persona-admin",
    password: "super-secret-password",
  });
});

