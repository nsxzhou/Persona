"use client";

import { PencilLine, PlugZap, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-sm uppercase tracking-[0.24em] text-stone-400">Model Configs</div>
          <h1 className="mt-2 text-3xl font-semibold">全局 Provider 配置</h1>
          <p className="mt-2 max-w-2xl text-sm text-stone-500">统一维护 OpenAI-compatible 网关配置。项目仅引用这里的默认项，不重复保存 API Key。</p>
        </div>
        <Button onClick={onOpenCreate}>
          <Plus className="mr-2 h-4 w-4" />
          新增配置
        </Button>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {providers.map((provider) => (
          <Card key={provider.id}>
            <CardHeader>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <CardTitle>{provider.label}</CardTitle>
                  <CardDescription>{provider.base_url}</CardDescription>
                </div>
                <Badge className={provider.is_enabled ? "bg-emerald-100 text-emerald-700" : "bg-stone-200 text-stone-700"}>
                  {provider.is_enabled ? "enabled" : "disabled"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2 text-sm text-stone-600">
                <div className="flex items-center justify-between gap-2">
                  <span>默认模型</span>
                  <span className="font-medium text-stone-900">{provider.default_model}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span>API Key</span>
                  <span className="font-medium text-stone-900">{provider.api_key_hint}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span>最近测试</span>
                  <span className="font-medium text-stone-900">{provider.last_test_status ?? "未测试"}</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => onTest(provider.id)}>
                  <PlugZap className="mr-2 h-4 w-4" />
                  测试连接
                </Button>
                <Button variant="secondary" onClick={() => onEdit?.(provider)}>
                  <PencilLine className="mr-2 h-4 w-4" />
                  编辑
                </Button>
                <Button variant="ghost" onClick={() => onDelete?.(provider.id)}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  删除
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

