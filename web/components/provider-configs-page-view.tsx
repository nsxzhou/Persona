"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { LoaderCircle, PencilLine, PlugZap, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { ProviderConfigFormDialog } from "@/components/provider-config-form-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ProviderConfig, ProviderPayload } from "@/lib/types";

export function ProviderConfigsPageClient() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);

  const providersQuery = useQuery({
    queryKey: ["provider-configs"],
    queryFn: api.getProviderConfigs,
  });

  const saveMutation = useMutation({
    mutationFn: async (payload: ProviderPayload) => {
      if (editingProvider) {
        return api.updateProviderConfig(editingProvider.id, payload);
      }
      return api.createProviderConfig(payload);
    },
    onError: (error) => toast.error(`保存失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("Provider 已保存");
      setDialogOpen(false);
      setEditingProvider(null);
      await queryClient.invalidateQueries({ queryKey: ["provider-configs"] });
    },
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => api.testProviderConfig(id),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProviderConfig(id),
    onError: (error) => toast.error(`删除失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("Provider 已删除");
      await queryClient.invalidateQueries({ queryKey: ["provider-configs"] });
    },
  });

  const handleTest = async (id: string) => {
    setTestingId(id);
    const toastId = toast.loading("正在测试连接…");
    try {
      const res = await testMutation.mutateAsync(id);
      toast.success(res.message || "测试完成", { id: toastId });
    } catch (error) {
      toast.error(
        `测试失败: ${error instanceof Error ? error.message : "未知错误"}`,
        { id: toastId },
      );
    } finally {
      setTestingId(null);
      await queryClient.invalidateQueries({ queryKey: ["provider-configs"] });
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
          await saveMutation.mutateAsync(values);
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
  onTest,
  onDelete,
}: {
  providers: ProviderConfig[];
  testingId?: string | null;
  onOpenCreate: () => void;
  onEdit?: (provider: ProviderConfig) => void;
  onTest: (id: string) => void;
  onDelete?: (id: string) => void;
}) {
  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
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
        {providers.map((provider) => (
          <div key={provider.id} className="rounded-xl border border-border bg-card text-card-foreground shadow-sm transition-all hover:ring-2 hover:ring-primary hover:border-transparent cursor-pointer">
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
              </div>
              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => onTest(provider.id)} disabled={testingId === provider.id}>
                  {testingId === provider.id ? (
                    <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <PlugZap className="mr-2 h-4 w-4" />
                  )}
                  {testingId === provider.id ? "测试中…" : "测试连接"}
                </Button>
                <Button variant="secondary" onClick={() => onEdit?.(provider)}>
                  <PencilLine className="mr-2 h-4 w-4" />编辑
                </Button>
                <Button variant="ghost" className="ml-auto text-red-600 hover:bg-red-100 hover:text-red-900" onClick={() => onDelete?.(provider.id)}>
                  <Trash2 className="mr-2 h-4 w-4" />删除
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
