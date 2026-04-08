"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { ProviderConfigFormDrawer } from "@/components/provider-config-form-drawer";
import { ProviderConfigsPageView } from "@/components/provider-configs-page-view";
import { api } from "@/lib/api";
import type { ProviderConfig, ProviderPayload } from "@/lib/types";

export default function ModelConfigsPage() {
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null);

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
      setDrawerOpen(false);
      setEditingProvider(null);
      await queryClient.invalidateQueries({ queryKey: ["provider-configs"] });
    },
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => api.testProviderConfig(id),
    onError: (error) => toast.error(`测试失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("测试完成");
      await queryClient.invalidateQueries({ queryKey: ["provider-configs"] });
    },
  });

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
    return <PageError title="Provider 列表加载失败" message={providersQuery.error instanceof Error ? providersQuery.error.message : "请重试"} />;
  }

  const providers = providersQuery.data;

  return (
    <div className="space-y-4">
      <ProviderConfigsPageView
        providers={providers}
        onDelete={(id) => deleteMutation.mutate(id)}
        onEdit={(provider) => {
          setEditingProvider(provider);
          setDrawerOpen(true);
        }}
        onOpenCreate={() => {
          setEditingProvider(null);
          setDrawerOpen(true);
        }}
        onTest={(id) => testMutation.mutate(id)}
      />
      <ProviderConfigFormDrawer
        open={drawerOpen}
        provider={editingProvider}
        submitting={saveMutation.isPending}
        onOpenChange={setDrawerOpen}
        onSubmit={async (values) => {
          await saveMutation.mutateAsync(values);
        }}
      />
    </div>
  );
}
