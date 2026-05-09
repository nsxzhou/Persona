"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Clipboard,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  Send,
  Settings,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type {
  ProviderChatTestMessage,
  ProviderChatTestResponse,
  ProviderConfig,
} from "@/lib/types";

const DEFAULT_SYSTEM_PROMPT = [
  "你是一位网文正文续写助手。",
  "根据用户给出的前文和续写要求，直接输出下一段正文。",
  "保持场景连续、动作清晰、对白自然，不要解释，不要输出思考过程。",
].join("\n");

type ChatMessage = ProviderChatTestMessage & {
  id: string;
  pending?: boolean;
};

let messageId = 0;

function createMessage(role: ProviderChatTestMessage["role"], content: string, pending = false) {
  messageId += 1;
  return { id: `provider-chat-message-${messageId}`, role, content, pending };
}

function toPayloadMessages(messages: ChatMessage[]): ProviderChatTestMessage[] {
  return messages
    .filter((message) => !message.pending)
    .map(({ role, content }) => ({ role, content }));
}

function clampTemperature(value: number) {
  return Math.min(2, Math.max(0, Number(value.toFixed(1))));
}

export function ProviderChatTestDialog({
  open,
  provider,
  submitting,
  onOpenChange,
  onSubmit,
  onSaveSystemPrompt,
}: {
  open: boolean;
  provider: ProviderConfig | null;
  submitting: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: {
    system_prompt: string;
    messages: ProviderChatTestMessage[];
    temperature: number;
  }) => Promise<ProviderChatTestResponse>;
  onSaveSystemPrompt?: (systemPrompt: string) => Promise<void>;
}) {
  const initialSystemPrompt =
    provider?.chat_test_system_prompt?.trim() ||
    provider?.immersion_system_prompt_suffix?.trim() ||
    DEFAULT_SYSTEM_PROMPT;
  const [systemPrompt, setSystemPrompt] = useState(initialSystemPrompt);
  const [temperature, setTemperature] = useState(0.7);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [latestResult, setLatestResult] = useState<ProviderChatTestResponse | null>(null);
  const [debugTab, setDebugTab] = useState("settings");
  const sessionIdRef = useRef(0);
  const lastSavedSystemPromptRef = useRef(initialSystemPrompt);

  useEffect(() => {
    if (open) {
      setSystemPrompt(initialSystemPrompt);
      lastSavedSystemPromptRef.current = initialSystemPrompt;
    } else {
      sessionIdRef.current += 1;
      setSystemPrompt(initialSystemPrompt);
      setTemperature(0.7);
      setDraft("");
      setMessages([]);
      setLatestResult(null);
      setDebugTab("settings");
    }
  }, [initialSystemPrompt, open]);

  const canSubmit = useMemo(
    () => Boolean(provider && systemPrompt.trim() && draft.trim() && !submitting),
    [draft, provider, submitting, systemPrompt],
  );

  const latestAssistantId = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].role === "assistant" && !messages[index].pending) {
        return messages[index].id;
      }
    }
    return null;
  }, [messages]);

  const canRegenerate = Boolean(provider && systemPrompt.trim() && latestAssistantId && !submitting);

  const modelLabel = provider?.default_model?.trim() || "未设置模型";

  const handleCopy = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      toast.success("已复制");
    } catch {
      toast.error("复制失败");
    }
  };

  const submitMessages = async (requestMessages: ProviderChatTestMessage[]) => {
    return await onSubmit({
      system_prompt: systemPrompt,
      messages: requestMessages,
      temperature,
    });
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;

    const currentSessionId = sessionIdRef.current;
    const userMessage = createMessage("user", draft.trim());
    const pendingMessage = createMessage("assistant", "正在生成回复...", true);
    const nextMessages = [...messages, userMessage];
    const requestMessages = toPayloadMessages(nextMessages);

    setMessages([...nextMessages, pendingMessage]);
    setDraft("");

    try {
      const result = await submitMessages(requestMessages);
      if (sessionIdRef.current !== currentSessionId) return;
      setLatestResult(result);
      setMessages([...nextMessages, createMessage("assistant", result.reply)]);
    } catch (error) {
      if (sessionIdRef.current !== currentSessionId) return;
      setMessages(nextMessages);
      toast.error(error instanceof Error ? error.message : "对话测试失败");
    }
  };

  const handleRegenerate = async () => {
    if (!canRegenerate) return;

    const currentSessionId = sessionIdRef.current;
    const assistantIndex = messages.findIndex((message) => message.id === latestAssistantId);
    if (assistantIndex === -1) return;

    const messagesBeforeAssistant = messages.slice(0, assistantIndex);
    const pendingMessage = createMessage("assistant", "正在重新生成...", true);
    const requestMessages = toPayloadMessages(messagesBeforeAssistant);

    setMessages([...messagesBeforeAssistant, pendingMessage]);

    try {
      const result = await submitMessages(requestMessages);
      if (sessionIdRef.current !== currentSessionId) return;
      setLatestResult(result);
      setMessages([...messagesBeforeAssistant, createMessage("assistant", result.reply)]);
    } catch (error) {
      if (sessionIdRef.current !== currentSessionId) return;
      setMessages(messages);
      toast.error(error instanceof Error ? error.message : "重新生成失败");
    }
  };

  const handleClearConversation = () => {
    sessionIdRef.current += 1;
    setDraft("");
    setMessages([]);
    setLatestResult(null);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      const trimmedSystemPrompt = systemPrompt.trim();
      if (
        trimmedSystemPrompt &&
        trimmedSystemPrompt !== lastSavedSystemPromptRef.current.trim()
      ) {
        void onSaveSystemPrompt?.(trimmedSystemPrompt)
          .then(() => {
            lastSavedSystemPromptRef.current = trimmedSystemPrompt;
            toast.success("测试 Prompt 已保存");
          })
          .catch((error) => {
            toast.error(
              error instanceof Error ? error.message : "测试 Prompt 自动保存失败",
            );
          });
      }
    }
    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="flex max-h-[92vh] max-w-6xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border/70 bg-background py-4 pl-6 pr-16">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div className="space-y-1">
              <DialogTitle>Provider 对话测试</DialogTitle>
              <DialogDescription>
                {provider?.label ?? "Provider"} · {modelLabel}
              </DialogDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground md:justify-end">
              <span className="rounded-full border border-border bg-muted/50 px-2.5 py-1">
                {systemPrompt.trim() === lastSavedSystemPromptRef.current.trim()
                  ? "测试 Prompt 已保存"
                  : "测试 Prompt 未保存"}
              </span>
              <span className="rounded-full border border-border bg-muted/50 px-2.5 py-1">
                Temperature {temperature.toFixed(1)}
              </span>
            </div>
          </div>
        </DialogHeader>

        <div className="grid min-h-0 flex-1 gap-0 overflow-y-auto bg-muted/20 lg:grid-cols-[minmax(0,1fr)_360px] lg:overflow-hidden">
          <section className="flex min-h-[620px] min-w-0 flex-col border-border/70 bg-background lg:border-r">
            <ScrollArea className="min-h-[360px] flex-1">
              <div className="space-y-5 p-5">
                {messages.length === 0 ? (
                  <div className="flex min-h-[350px] flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/30 px-6 text-center">
                    <div className="mb-4 rounded-full border border-border bg-background p-3 shadow-sm">
                      <MessageSquareText className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div className="text-sm font-medium text-foreground">
                      {provider?.label ?? "Provider"} · {modelLabel}
                    </div>
                    <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                      输入一段用户消息开始测试。当前测试 System Prompt 和 Temperature 会应用到下一次发送。
                    </p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <article
                      key={message.id}
                      className={cn(
                        "flex",
                        message.role === "user" ? "justify-end" : "justify-start",
                      )}
                    >
                      <div
                        className={cn(
                          "group max-w-[86%] rounded-2xl border px-4 py-3 text-sm shadow-sm",
                          message.role === "user"
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border bg-background",
                          message.pending && "text-muted-foreground",
                        )}
                      >
                        <div className="mb-1.5 flex items-center justify-between gap-3">
                          <span className="text-xs font-medium opacity-75">
                            {message.role === "user" ? "User" : "Assistant"}
                          </span>
                          {!message.pending ? (
                            <div className="flex items-center gap-1 opacity-100 md:opacity-0 md:transition-opacity md:group-hover:opacity-100">
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className={cn(
                                  "h-7 w-7",
                                  message.role === "user" &&
                                    "text-primary-foreground hover:bg-primary-foreground/15 hover:text-primary-foreground",
                                )}
                                aria-label="复制消息"
                                onClick={() => void handleCopy(message.content)}
                              >
                                <Clipboard className="h-3.5 w-3.5" />
                              </Button>
                              {message.id === latestAssistantId ? (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7"
                                  aria-label="重新生成最新回复"
                                  disabled={!canRegenerate}
                                  onClick={() => void handleRegenerate()}
                                >
                                  <RefreshCw className="h-3.5 w-3.5" />
                                </Button>
                              ) : null}
                            </div>
                          ) : (
                            <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                          )}
                        </div>
                        <div className="whitespace-pre-wrap break-words leading-6">
                          {message.content}
                        </div>
                      </div>
                    </article>
                  ))
                )}
              </div>
            </ScrollArea>

            <div className="border-t border-border/70 bg-background p-4">
              <div className="grid gap-2">
                <Label htmlFor="provider-chat-message">用户消息</Label>
                <Textarea
                  id="provider-chat-message"
                  className="min-h-[92px] resize-none rounded-xl bg-muted/30"
                  placeholder="输入测试消息..."
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      void handleSubmit();
                    }
                  }}
                />
                <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <Button
                    type="button"
                    variant="outline"
                    className="sm:w-auto"
                    disabled={messages.length === 0 && draft.length === 0 && !latestResult}
                    onClick={handleClearConversation}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    清空对话
                  </Button>
                  <Button type="button" disabled={!canSubmit} onClick={() => void handleSubmit()}>
                    {submitting ? (
                      <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="mr-2 h-4 w-4" />
                    )}
                    发送测试
                  </Button>
                </div>
              </div>
            </div>
          </section>

          <aside className="min-h-0 bg-muted/30 p-4">
            <Tabs value={debugTab} onValueChange={setDebugTab} className="flex h-full min-h-0 flex-col">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="settings" onClick={() => setDebugTab("settings")}>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </TabsTrigger>
                <TabsTrigger value="request" onClick={() => setDebugTab("request")}>
                  Actual request
                </TabsTrigger>
              </TabsList>

              <TabsContent value="settings" className="mt-4 min-h-0 flex-1 space-y-4">
                  <div className="rounded-lg border border-border bg-background p-4 shadow-sm">
                    <div className="grid gap-2">
                      <Label htmlFor="provider-chat-system-prompt">System Prompt</Label>
                      <Textarea
                        id="provider-chat-system-prompt"
                        className="min-h-[220px] resize-y font-mono text-sm leading-6"
                        value={systemPrompt}
                        onChange={(event) => setSystemPrompt(event.target.value)}
                      />
                    </div>
                  </div>

                  <div className="rounded-lg border border-border bg-background p-4 shadow-sm">
                    <div className="grid gap-3">
                      <div className="flex items-center justify-between gap-3">
                        <Label htmlFor="provider-chat-temperature-range">Temperature</Label>
                        <Input
                          id="provider-chat-temperature"
                          aria-label="Temperature 数值"
                          type="number"
                          min={0}
                          max={2}
                          step={0.1}
                          className="h-9 w-24"
                          value={temperature}
                          onChange={(event) => {
                            const next = event.target.valueAsNumber;
                            if (!Number.isNaN(next)) {
                              setTemperature(clampTemperature(next));
                            }
                          }}
                        />
                      </div>
                      <input
                        id="provider-chat-temperature-range"
                        aria-label="Temperature"
                        type="range"
                        min={0}
                        max={2}
                        step={0.1}
                        value={temperature}
                        className="w-full accent-primary"
                        onChange={(event) =>
                          setTemperature(clampTemperature(event.target.valueAsNumber))
                        }
                      />
                    </div>
                  </div>

                  <div className="rounded-lg border border-border bg-background p-4 text-sm shadow-sm">
                    <div className="flex justify-between gap-4">
                      <span className="text-muted-foreground">测试 Prompt</span>
                      <span>
                        {systemPrompt.trim() === lastSavedSystemPromptRef.current.trim()
                          ? "已保存"
                          : "未保存"}
                      </span>
                    </div>
                    <div className="mt-2 flex justify-between gap-4">
                      <span className="text-muted-foreground">默认来源</span>
                      <span>
                        {provider?.chat_test_system_prompt?.trim()
                          ? "测试 Prompt"
                          : provider?.immersion_system_prompt_suffix?.trim()
                            ? "Provider 追加内容"
                            : "内置默认"}
                      </span>
                    </div>
                    <div className="mt-2 flex justify-between gap-4">
                      <span className="text-muted-foreground">返回 Temperature</span>
                      <span>{latestResult?.temperature ?? "尚未发送"}</span>
                    </div>
                  </div>
              </TabsContent>
              <TabsContent value="request" className="mt-4 min-h-0 flex-1">
                <ScrollArea className="h-[520px] rounded-lg border border-border bg-background shadow-sm lg:h-full">
                  <div className="space-y-3 p-4">
                    {latestResult?.sent_messages.length ? (
                      latestResult.sent_messages.map((message, index) => (
                        <div key={`${message.role}-${index}`} className="space-y-1.5">
                          <div className="text-xs font-medium uppercase text-muted-foreground">
                            {message.role}
                          </div>
                          <pre className="whitespace-pre-wrap break-words rounded-lg bg-muted/60 p-3 text-xs leading-5">
                            {message.content}
                          </pre>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm leading-6 text-muted-foreground">
                        发送后显示 actual request 的 sent_messages。
                      </p>
                    )}
                  </div>
                </ScrollArea>
              </TabsContent>
            </Tabs>
          </aside>
        </div>
      </DialogContent>
    </Dialog>
  );
}
