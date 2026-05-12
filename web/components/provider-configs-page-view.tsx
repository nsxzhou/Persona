"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { LoaderCircle, MessageSquare, MessageSquareText, PencilLine, PlugZap, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { ProviderChatTestDialog } from "@/components/provider-chat-test-dialog";
import { ProviderConfigFormDialog } from "@/components/provider-config-form-dialog";
import { ProviderPromptOverrideDialog } from "@/components/provider-prompt-override-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { providerQueryKeys } from "@/lib/provider-query-keys";
import type {
  ProviderConfig,
  ProviderChatTestRequest,
  ProviderConfigCreatePayload,
  ProviderConfigUpdatePayload,
} from "@/lib/types";

type ProviderSaveRequest =
  | { type: "create"; payload: ProviderConfigCreatePayload }
  | { type: "update"; providerId: string; payload: ProviderConfigUpdatePayload };

export function ProviderConfigsPageClient() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null);
  const [promptProvider, setPromptProvider] = useState<ProviderConfig | null>(null);
  const [promptDialogOpen, setPromptDialogOpen] = useState(false);
  const [chatProvider, setChatProvider] = useState<ProviderConfig | null>(null);
  const [chatDialogOpen, setChatDialogOpen] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);

  const providersQuery = useQuery({
    queryKey: providerQueryKeys.lists(),
    queryFn: api.getProviderConfigs,
  });

  const saveMutation = useMutation({
    mutationFn: async (request: ProviderSaveRequest) => {
      if (request.type === "update") {
        return api.updateProviderConfig(request.providerId, request.payload);
      }
      return api.createProviderConfig(request.payload);
    },
    onError: (error) => toast.error(error.message),
    onSuccess: async () => {
      toast.success("Provider 已保存");
      setDialogOpen(false);
      setEditingProvider(null);
      await queryClient.invalidateQueries({ queryKey: providerQueryKeys.lists() });
    },
  });

  const promptSaveMutation = useMutation({
    mutationFn: async (payload: Pick<
      ProviderConfigUpdatePayload,
      "immersion_prompt_override_enabled" | "immersion_system_prompt_suffix"
    >) => {
      if (!promptProvider) {
        throw new Error("Provider 不存在");
      }
      return api.updateProviderConfig(promptProvider.id, payload);
    },
    onError: (error) => toast.error(error.message),
    onSuccess: async () => {
      toast.success("Provider 提示词已保存");
      setPromptDialogOpen(false);
      setPromptProvider(null);
      await queryClient.invalidateQueries({ queryKey: providerQueryKeys.lists() });
    },
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => api.testProviderConfig(id),
  });

  const chatTestMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ProviderChatTestRequest }) =>
      api.chatTestProviderConfig(id, payload),
    onError: (error) => toast.error(error.message),
  });

  const chatPromptSaveMutation = useMutation({
    mutationFn: async ({
      id,
      systemPrompt,
    }: {
      id: string;
      systemPrompt: string;
    }) => api.updateProviderConfig(id, { chat_test_system_prompt: systemPrompt }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: providerQueryKeys.lists() });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProviderConfig(id),
    onError: (error) => toast.error(error.message),
    onSuccess: async (_, deletedId) => {
      toast.success("Provider 已删除");
      queryClient.setQueryData<ProviderConfig[]>(providerQueryKeys.lists(), (current) => {
        if (!current) return current;
        return current.filter((provider) => provider.id !== deletedId);
      });
      await queryClient.invalidateQueries({
        queryKey: providerQueryKeys.lists(),
        refetchType: "none",
      });
    },
  });

  const handleTest = async (id: string) => {
    setTestingId(id);
    const toastId = toast.loading("正在测试连接…");
    try {
      const res = await testMutation.mutateAsync(id);
      if (res.status === "error") {
        toast.error(res.message || "连接失败", { id: toastId });
      } else {
        toast.success(res.message || "测试完成", { id: toastId });
      }
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "未知错误",
        { id: toastId },
      );
    } finally {
      setTestingId(null);
      await queryClient.invalidateQueries({ queryKey: providerQueryKeys.lists() });
    }
  };

  if (providersQuery.isLoading) {
    return <PageLoading />;
  }

  if (providersQuery.isError || !providersQuery.data) {
    return (
      <PageError
        title="Provider 列表加载失败"
        message={providersQuery.error instanceof Error ? providersQuery.error.message : "请重试"}
      />
    );
  }

  return (
    <div className="space-y-4">
      <ProviderConfigsPageView
        providers={providersQuery.data}
        testingId={testingId}
        onDelete={(id) => deleteMutation.mutate(id)}
        onEdit={(provider) => {
          setEditingProvider(provider);
          setDialogOpen(true);
        }}
        onEditPrompt={(provider) => {
          setPromptProvider(provider);
          setPromptDialogOpen(true);
        }}
        onOpenChat={(provider) => {
          setChatProvider(provider);
          setChatDialogOpen(true);
        }}
        onOpenCreate={() => {
          setEditingProvider(null);
          setDialogOpen(true);
        }}
        onTest={handleTest}
      />
      <ProviderConfigFormDialog
        open={dialogOpen}
        provider={editingProvider}
        submitting={saveMutation.isPending}
        onOpenChange={setDialogOpen}
        onSubmit={async (values) => {
          const payload = {
            ...values,
            api_key: values.api_key ?? "",
          };
          await saveMutation.mutateAsync(
            editingProvider
              ? {
                  type: "update",
                  providerId: editingProvider.id,
                  payload,
                }
              : {
                  type: "create",
                  payload: {
                    ...payload,
                    immersion_prompt_override_enabled: false,
                    immersion_system_prompt_suffix: "",
                    chat_test_system_prompt: "",
                  },
                },
          );
        }}
      />
      <ProviderPromptOverrideDialog
        open={promptDialogOpen}
        provider={promptProvider}
        submitting={promptSaveMutation.isPending}
        onOpenChange={(open) => {
          setPromptDialogOpen(open);
          if (!open) setPromptProvider(null);
        }}
        onSubmit={async (values) => {
          await promptSaveMutation.mutateAsync(values);
        }}
      />
      <ProviderChatTestDialog
        open={chatDialogOpen}
        provider={chatProvider}
        submitting={chatTestMutation.isPending}
        onOpenChange={(open) => {
          setChatDialogOpen(open);
          if (!open) setChatProvider(null);
        }}
        onSaveSystemPrompt={async (systemPrompt) => {
          if (!chatProvider) {
            throw new Error("Provider 不存在");
          }
          await chatPromptSaveMutation.mutateAsync({
            id: chatProvider.id,
            systemPrompt,
          });
        }}
        onSubmit={async (payload) => {
          if (!chatProvider) {
            throw new Error("Provider 不存在");
          }
          return await chatTestMutation.mutateAsync({ id: chatProvider.id, payload });
        }}
      />
    </div>
  );
}

export function ProviderConfigsPageView({
  providers,
  testingId,
  onOpenCreate,
  onEdit,
  onEditPrompt,
  onOpenChat,
  onTest,
  onDelete,
}: {
  providers: ProviderConfig[];
  testingId?: string | null;
  onOpenCreate: () => void;
  onEdit?: (provider: ProviderConfig) => void;
  onEditPrompt?: (provider: ProviderConfig) => void;
  onOpenChat?: (provider: ProviderConfig) => void;
  onTest: (id: string) => void;
  onDelete?: (id: string) => void;
}) {
  return (
    <section className="motion-page space-y-6">
      <div className="animate-slide-up flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">全局 Provider 配置</h1>
          <p className="mt-1 text-sm text-muted-foreground">统一维护 OpenAI-compatible 网关配置。</p>
        </div>
        <Button onClick={onOpenCreate}>
          <Plus className="mr-2 h-4 w-4" />
          新增配置
        </Button>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {providers.map((provider, index) => (
          <div
            key={provider.id}
            className="motion-surface animate-scale-in rounded-xl border border-border bg-card text-card-foreground shadow-sm hover:ring-2 hover:ring-primary hover:border-transparent cursor-pointer"
            data-interactive="true"
            style={{ "--motion-delay": `${index * 45}ms` } as React.CSSProperties}
          >
            <div className="flex flex-col space-y-1.5 p-6 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold leading-none tracking-tight">{provider.label}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground">{provider.base_url}</p>
                </div>
                {provider.is_enabled ? (
                  <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">已启用</Badge>
                ) : (
                  <Badge variant="secondary" className="bg-zinc-100 text-zinc-700 hover:bg-zinc-100">已禁用</Badge>
                )}
              </div>
            </div>
            <div className="space-y-4 p-6 pt-0">
              <div className="grid gap-2 text-sm text-muted-foreground">
                <div className="flex justify-between">
                  <span>默认模型</span>
                  <span className="font-medium text-foreground">{provider.default_model}</span>
                </div>
                <div className="flex justify-between">
                  <span>API Key</span>
                  <span className="font-medium text-foreground">{provider.api_key_hint}</span>
                </div>
                <div className="flex justify-between">
                  <span>最近测试</span>
                  <span className="font-medium text-foreground">{provider.last_test_status ?? "未测试"}</span>
                </div>
                <div className="flex justify-between">
                  <span>提示词追加</span>
                  <span className="font-medium text-foreground">
                    {provider.immersion_prompt_override_enabled ? "已启用" : "未启用"}
                  </span>
                </div>
              </div>
              <div className="grid gap-2 pt-2">
                <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  className="min-w-[150px] flex-1 sm:flex-none"
                  onClick={() => onTest(provider.id)}
                  disabled={testingId === provider.id}
                >
                  {testingId === provider.id ? (
                    <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <PlugZap className="mr-2 h-4 w-4" />
                  )}
                  {testingId === provider.id ? "测试中…" : "测试连接"}
                </Button>
                <Button
                  variant="outline"
                  className="min-w-[132px] flex-1 sm:flex-none"
                  onClick={() => onEditPrompt?.(provider)}
                >
                  <MessageSquareText className="mr-2 h-4 w-4" />提示词
                </Button>
                <Button
                  variant="outline"
                  className="min-w-[132px] flex-1 sm:flex-none"
                  onClick={() => onOpenChat?.(provider)}
                >
                  <MessageSquare className="mr-2 h-4 w-4" />对话测试
                </Button>
                <Button
                  variant="secondary"
                  className="min-w-[116px] flex-1 sm:flex-none"
                  onClick={() => onEdit?.(provider)}
                >
                  <PencilLine className="mr-2 h-4 w-4" />编辑
                </Button>
                </div>
                <div className="flex justify-end">
                  <Button
                    variant="ghost"
                    className="text-red-600 hover:bg-red-100 hover:text-red-900"
                    onClick={() => onDelete?.(provider.id)}
                  >
                  <Trash2 className="mr-2 h-4 w-4" />删除
                  </Button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
