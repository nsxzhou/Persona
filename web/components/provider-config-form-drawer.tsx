"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ProviderConfig, ProviderPayload } from "@/lib/types";

const schema = z.object({
  label: z.string().min(1),
  base_url: z.string().min(1),
  api_key: z.string().optional(),
  default_model: z.string().min(1),
  is_enabled: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

export function ProviderConfigFormDrawer({
  open,
  provider,
  submitting,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  provider: ProviderConfig | null;
  submitting: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: ProviderPayload) => Promise<void>;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema, undefined, { mode: "sync" }),
    defaultValues: {
      label: "",
      base_url: "https://api.openai.com/v1",
      api_key: "",
      default_model: "gpt-4.1-mini",
      is_enabled: true,
    },
  });

  useEffect(() => {
    form.reset({
      label: provider?.label ?? "",
      base_url: provider?.base_url ?? "https://api.openai.com/v1",
      api_key: "",
      default_model: provider?.default_model ?? "gpt-4.1-mini",
      is_enabled: provider?.is_enabled ?? true,
    });
  }, [form, provider]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{provider ? "编辑 Provider 配置" : "新增 Provider 配置"}</DialogTitle>
          <DialogDescription>API Key 只写入后台加密存储，前端不会回显明文。</DialogDescription>
        </DialogHeader>
        <form className="mt-6 grid gap-5" onSubmit={form.handleSubmit(async (values) => onSubmit(values))}>
          <div className="grid gap-2">
            <Label htmlFor="provider-form-label">名称</Label>
            <Input id="provider-form-label" {...form.register("label")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="provider-form-base-url">Base URL</Label>
            <Input id="provider-form-base-url" {...form.register("base_url")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="provider-form-api-key">API Key</Label>
            <Input id="provider-form-api-key" type="password" placeholder={provider ? "留空则保留原值" : ""} {...form.register("api_key")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="provider-form-default-model">默认模型</Label>
            <Input id="provider-form-default-model" {...form.register("default_model")} />
          </div>
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input className="h-4 w-4" type="checkbox" {...form.register("is_enabled")} />
            启用该配置
          </label>
          <Button type="submit" disabled={submitting}>
            {provider ? "保存修改" : "创建配置"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
