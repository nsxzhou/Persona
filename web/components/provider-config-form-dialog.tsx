"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { type FieldError, useForm } from "react-hook-form";
import { z } from "zod";

import { ProviderFormFields } from "@/components/provider-form-fields";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { ProviderConfig, ProviderPayload } from "@/lib/types";
import { createProviderFormDefaults, createProviderFormSchema } from "@/lib/validations/provider";

const schema = createProviderFormSchema();

type FormValues = z.infer<typeof schema>;

export function ProviderConfigFormDialog({
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
  onSubmit: (values: FormValues) => Promise<void>;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema, undefined, { mode: "sync" }),
    defaultValues: createProviderFormDefaults(),
  });

  useEffect(() => {
    form.reset(createProviderFormDefaults(provider));
  }, [form, provider]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{provider ? "编辑 Provider 配置" : "新增 Provider 配置"}</DialogTitle>
          <DialogDescription>API Key 只写入后台加密存储，前端不会回显明文。</DialogDescription>
        </DialogHeader>
        <form className="mt-6 grid gap-5" onSubmit={form.handleSubmit(onSubmit)}>
          <ProviderFormFields
            ids={{
              label: "provider-form-label",
              baseUrl: "provider-form-base-url",
              apiKey: "provider-form-api-key",
              defaultModel: "provider-form-default-model",
              isEnabled: "provider-form-is-enabled",
            }}
            labelField={form.register("label")}
            baseUrlField={form.register("base_url")}
            apiKeyField={form.register("api_key")}
            defaultModelField={form.register("default_model")}
            showEnabled
            isEnabled={form.watch("is_enabled")}
            onEnabledChange={(checked) => form.setValue("is_enabled", checked)}
            placeholders={{
              apiKey: provider ? "留空则保留原值" : "",
            }}
            errors={{
              label: form.formState.errors.label as FieldError | undefined,
              base_url: form.formState.errors.base_url as FieldError | undefined,
              api_key: form.formState.errors.api_key as FieldError | undefined,
              default_model: form.formState.errors.default_model as FieldError | undefined,
            }}
          />
          <Button type="submit" disabled={submitting}>
            {provider ? "保存修改" : "创建配置"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
