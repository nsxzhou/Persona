"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { ProviderConfigFormDialog } from "@/components/provider-config-form-dialog";
import { ProviderConfigsPageView } from "@/components/provider-configs-page-view";
import { api } from "@/lib/api";
import type { ProviderConfig, ProviderPayload } from "@/lib/types";

export default function ModelConfigsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(
    null,
  );
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

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProviderConfig(id),
    onError: (error) => toast.error(`删除失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("Provider 已删除");
      await queryClient.invalidateQueries({ queryKey: ["provider-configs"] });
    },
  });

  if (providersQuery.isLoading) {
    return <PageLoading />;
  }

  if (providersQuery.isError || !providersQuery.data) {
    return (
      <PageError
        title="Provider 列表加载失败"
        message={
          providersQuery.error instanceof Error
            ? providersQuery.error.message
            : "请重试"
        }
      />
    );
  }

  const providers = providersQuery.data;

  return (
    <div className="space-y-4">
      <ProviderConfigsPageView
        providers={providers}
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
