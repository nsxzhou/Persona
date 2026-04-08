"use client";

import { PencilLine, PlugZap, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ProviderConfig } from "@/lib/types";

export function ProviderConfigsPageView({
  providers,
  onOpenCreate,
  onEdit,
  onTest,
  onDelete,
}: {
  providers: ProviderConfig[];
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
          <div key={provider.id} className="rounded-xl border border-border bg-card text-card-foreground shadow-sm">
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
                <Button variant="outline" onClick={() => onTest(provider.id)}>
                  <PlugZap className="mr-2 h-4 w-4" />测试连接
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