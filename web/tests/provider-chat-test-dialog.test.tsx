import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { ProviderChatTestDialog } from "@/components/provider-chat-test-dialog";
import type {
  ProviderChatTestResponse,
  ProviderConfig,
} from "@/lib/types";

const toastMock = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
}));

vi.mock("sonner", () => ({ toast: toastMock }));

const provider: ProviderConfig = {
  id: "provider-1",
  label: "Primary Gateway",
  base_url: "https://api.openai.com/v1",
  default_model: "gpt-4.1-mini",
  api_key_hint: "****1234",
  is_enabled: true,
  immersion_prompt_override_enabled: true,
  immersion_system_prompt_suffix: "Provider suffix",
  chat_test_system_prompt: "Saved chat test prompt",
  last_test_status: null,
  last_test_error: null,
  last_tested_at: null,
  created_at: "2026-04-09T00:00:00Z",
  updated_at: "2026-04-09T00:00:00Z",
};

function createResponse(reply: string): ProviderChatTestResponse {
  return {
    reply,
    sent_messages: [
      { role: "system", content: "SYSTEM" },
      { role: "user", content: "第一句" },
      { role: "assistant", content: "上一轮回复" },
      { role: "user", content: "继续" },
    ],
    provider_prompt_override_applied: false,
    temperature: 0.4,
  };
}

function renderDialog({
  open = true,
  submitting = false,
  onOpenChange = () => undefined,
  onSubmit = vi.fn().mockResolvedValue(createResponse("模型回复")),
}: {
  open?: boolean;
  submitting?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSubmit?: (payload: {
    system_prompt: string;
    messages: { role: "user" | "assistant"; content: string }[];
    temperature: number;
  }) => Promise<ProviderChatTestResponse>;
} = {}) {
  return render(
    <ProviderChatTestDialog
      open={open}
      provider={provider}
      submitting={submitting}
      onOpenChange={onOpenChange}
      onSubmit={onSubmit}
    />,
  );
}

test("provider chat dialog sends payload and renders reply plus actual request", async () => {
  const onSubmit = vi.fn().mockResolvedValue(createResponse("模型回复"));
  renderDialog({ onSubmit });

  fireEvent.change(screen.getByLabelText("用户消息"), {
    target: { value: "第一句" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送测试" }));

  expect(screen.getByText("第一句")).toBeInTheDocument();
  expect(screen.getByText("正在生成回复...")).toBeInTheDocument();

  await waitFor(() => {
    expect(onSubmit).toHaveBeenCalledWith({
      system_prompt: "Saved chat test prompt",
      messages: [{ role: "user", content: "第一句" }],
      temperature: 0.7,
    });
  });

  expect(await screen.findByText("模型回复")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "Actual request" }));
  expect(await screen.findByText(/SYSTEM/)).toBeInTheDocument();
  expect(screen.getAllByText(/第一句/).length).toBeGreaterThanOrEqual(2);
  expect(screen.queryByText(/Provider suffix/)).not.toBeInTheDocument();
  expect(screen.queryByText(/正文沉浸要求/)).not.toBeInTheDocument();
});

test("provider chat dialog sends with Enter and preserves newline with Shift Enter", async () => {
  const onSubmit = vi.fn().mockResolvedValue(createResponse("模型回复"));
  renderDialog({ onSubmit });

  const messageInput = screen.getByLabelText("用户消息");
  fireEvent.change(messageInput, {
    target: { value: "第一句\n第二句" },
  });
  fireEvent.keyDown(messageInput, { key: "Enter", shiftKey: true });

  expect(messageInput).toHaveValue("第一句\n第二句");
  expect(onSubmit).not.toHaveBeenCalled();

  fireEvent.keyDown(messageInput, { key: "Enter" });

  await waitFor(() => {
    expect(onSubmit).toHaveBeenCalledWith({
      system_prompt: expect.any(String),
      messages: [{ role: "user", content: "第一句\n第二句" }],
      temperature: 0.7,
    });
  });
});

test("provider chat dialog clears conversation while preserving prompt and temperature", async () => {
  const onSubmit = vi.fn().mockResolvedValue(createResponse("模型回复"));
  renderDialog({ onSubmit });

  fireEvent.click(screen.getByRole("tab", { name: /Settings/ }));
  fireEvent.change(screen.getByLabelText("System Prompt"), {
    target: { value: "CUSTOM SYSTEM" },
  });
  fireEvent.change(screen.getByLabelText("Temperature"), {
    target: { value: "1.2" },
  });

  fireEvent.change(screen.getByLabelText("用户消息"), {
    target: { value: "第一句" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送测试" }));
  expect(await screen.findByText("模型回复")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("用户消息"), {
    target: { value: "临时草稿" },
  });
  fireEvent.click(screen.getByRole("button", { name: "清空对话" }));

  expect(screen.queryByText("模型回复")).not.toBeInTheDocument();
  expect(screen.getByLabelText("用户消息")).toHaveValue("");
  expect(screen.getByLabelText("System Prompt")).toHaveValue("CUSTOM SYSTEM");
  expect(screen.getByLabelText("Temperature")).toHaveValue("1.2");
});

test("provider chat dialog regenerates by replacing latest assistant reply", async () => {
  const onSubmit = vi
    .fn()
    .mockResolvedValueOnce(createResponse("第一次回复"))
    .mockResolvedValueOnce(createResponse("重新生成回复"));
  renderDialog({ onSubmit });

  fireEvent.change(screen.getByLabelText("用户消息"), {
    target: { value: "第一句" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送测试" }));

  expect(await screen.findByText("第一次回复")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "重新生成最新回复" }));

  expect(await screen.findByText("重新生成回复")).toBeInTheDocument();
  expect(screen.queryByText("第一次回复")).not.toBeInTheDocument();
  expect(screen.getAllByText("第一句")).toHaveLength(1);

  expect(onSubmit).toHaveBeenLastCalledWith({
    system_prompt: expect.any(String),
    messages: [{ role: "user", content: "第一句" }],
    temperature: 0.7,
  });
});

test("provider chat dialog clears temporary state when closed", () => {
  const { rerender } = render(
    <ProviderChatTestDialog
      open
      provider={provider}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={async () => createResponse("")}
    />,
  );

  fireEvent.click(screen.getByRole("tab", { name: /Settings/ }));
  fireEvent.change(screen.getByLabelText("System Prompt"), {
    target: { value: "CUSTOM SYSTEM" },
  });
  fireEvent.change(screen.getByLabelText("Temperature"), {
    target: { value: "1.4" },
  });
  fireEvent.change(screen.getByLabelText("用户消息"), {
    target: { value: "临时内容" },
  });

  rerender(
    <ProviderChatTestDialog
      open={false}
      provider={provider}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={async () => createResponse("")}
    />,
  );

  rerender(
    <ProviderChatTestDialog
      open
      provider={provider}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={async () => createResponse("")}
    />,
  );

  expect(screen.getByLabelText("用户消息")).toHaveValue("");
  expect(screen.getByLabelText("System Prompt")).toHaveValue(
    "Saved chat test prompt",
  );
  expect(screen.getByLabelText("Temperature")).toHaveValue("0.7");
});

test("provider chat dialog ignores in-flight response after close and reopen", async () => {
  let resolveSubmit: ((response: ProviderChatTestResponse) => void) | undefined;
  const onSubmit = vi.fn(
    () =>
      new Promise<ProviderChatTestResponse>((resolve) => {
        resolveSubmit = resolve;
      }),
  );

  const { rerender } = render(
    <ProviderChatTestDialog
      open
      provider={provider}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={onSubmit}
    />,
  );

  fireEvent.change(screen.getByLabelText("用户消息"), {
    target: { value: "第一句" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送测试" }));

  expect(screen.getByText("正在生成回复...")).toBeInTheDocument();

  rerender(
    <ProviderChatTestDialog
      open={false}
      provider={provider}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={onSubmit}
    />,
  );

  rerender(
    <ProviderChatTestDialog
      open
      provider={provider}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={onSubmit}
    />,
  );

  resolveSubmit?.(createResponse("延迟回复"));
  await waitFor(() => {
    expect(screen.queryByText("延迟回复")).not.toBeInTheDocument();
  });
  expect(screen.getByLabelText("用户消息")).toHaveValue("");
  expect(screen.getByLabelText("System Prompt")).toHaveValue(
    "Saved chat test prompt",
  );
});

test("provider chat dialog initializes prompt from saved prompt, suffix, then built-in default", () => {
  const { rerender } = render(
    <ProviderChatTestDialog
      open
      provider={provider}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={async () => createResponse("")}
    />,
  );

  expect(screen.getByLabelText("System Prompt")).toHaveValue("Saved chat test prompt");

  rerender(
    <ProviderChatTestDialog
      open
      provider={{
        ...provider,
        chat_test_system_prompt: "",
        immersion_system_prompt_suffix: "Provider suffix",
      }}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={async () => createResponse("")}
    />,
  );

  expect(screen.getByLabelText("System Prompt")).toHaveValue("Provider suffix");

  rerender(
    <ProviderChatTestDialog
      open
      provider={{
        ...provider,
        chat_test_system_prompt: "",
        immersion_system_prompt_suffix: "",
      }}
      submitting={false}
      onOpenChange={() => undefined}
      onSubmit={async () => createResponse("")}
    />,
  );

  expect(screen.getByLabelText("System Prompt")).toHaveValue(
    "你是一位网文正文续写助手。\n根据用户给出的前文和续写要求，直接输出下一段正文。\n保持场景连续、动作清晰、对白自然，不要解释，不要输出思考过程。",
  );
});

test("provider chat dialog autosaves system prompt on close when changed", async () => {
  const onSaveSystemPrompt = vi.fn().mockResolvedValue(undefined);
  const onOpenChange = vi.fn();

  render(
    <ProviderChatTestDialog
      open
      provider={provider}
      submitting={false}
      onOpenChange={onOpenChange}
      onSubmit={async () => createResponse("")}
      onSaveSystemPrompt={onSaveSystemPrompt}
    />,
  );

  fireEvent.click(screen.getByRole("tab", { name: /Settings/ }));
  fireEvent.change(screen.getByLabelText("System Prompt"), {
    target: { value: "Updated prompt" },
  });

  fireEvent.keyDown(document.body, { key: "Escape" });

  await waitFor(() => {
    expect(onSaveSystemPrompt).toHaveBeenCalledWith("Updated prompt");
  });
  await waitFor(() => {
    expect(toastMock.success).toHaveBeenCalledWith("测试 Prompt 已保存");
  });
  expect(onOpenChange).toHaveBeenCalledWith(false);
});

test("provider chat dialog skips autosave on close when prompt unchanged", async () => {
  const onSaveSystemPrompt = vi.fn();
  const onOpenChange = vi.fn();

  render(
    <ProviderChatTestDialog
      open
      provider={provider}
      submitting={false}
      onOpenChange={onOpenChange}
      onSubmit={async () => createResponse("")}
      onSaveSystemPrompt={onSaveSystemPrompt}
    />,
  );

  fireEvent.keyDown(document.body, { key: "Escape" });

  await waitFor(() => {
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
  expect(onSaveSystemPrompt).not.toHaveBeenCalled();
});

test("provider chat dialog shows error toast when autosave fails but still closes", async () => {
  const onSaveSystemPrompt = vi.fn().mockRejectedValue(new Error("网络错误"));
  const onOpenChange = vi.fn();

  render(
    <ProviderChatTestDialog
      open
      provider={provider}
      submitting={false}
      onOpenChange={onOpenChange}
      onSubmit={async () => createResponse("")}
      onSaveSystemPrompt={onSaveSystemPrompt}
    />,
  );

  fireEvent.click(screen.getByRole("tab", { name: /Settings/ }));
  fireEvent.change(screen.getByLabelText("System Prompt"), {
    target: { value: "Will fail" },
  });

  fireEvent.keyDown(document.body, { key: "Escape" });

  await waitFor(() => {
    expect(toastMock.error).toHaveBeenCalledWith("网络错误");
  });
  expect(onOpenChange).toHaveBeenCalledWith(false);
});
