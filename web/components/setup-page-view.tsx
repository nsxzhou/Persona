"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { SetupPayload } from "@/lib/types";

const schema = z.object({
  username: z.string().min(3),
  password: z.string().min(8),
  provider: z.object({
    label: z.string().min(1),
    base_url: z.string().min(1),
    api_key: z.string().min(4),
    default_model: z.string().min(1),
    is_enabled: z.boolean(),
  }),
});

type FormValues = z.infer<typeof schema>;

export function SetupPageView({
  onSubmit,
  submitting,
}: {
  onSubmit: (values: SetupPayload) => Promise<void> | void;
  submitting: boolean;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema, undefined, { mode: "sync" }),
    defaultValues: {
      username: "",
      password: "",
      provider: {
        label: "",
        base_url: "https://api.openai.com/v1",
        api_key: "",
        default_model: "gpt-4.1-mini",
        is_enabled: true,
      },
    },
  });

  const handleSubmit = () => {
    const values = schema.parse({
      ...form.getValues(),
      provider: {
        ...form.getValues("provider"),
        is_enabled: true,
      },
    });
    void onSubmit(values);
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <Card className="overflow-hidden border-stone-200 bg-white/95">
        <CardHeader className="border-b border-stone-100 bg-stone-50/80">
          <CardTitle>初始化 Persona</CardTitle>
          <CardDescription>首次部署只需一次：创建管理员账号，并接入首个 OpenAI-compatible Provider。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 py-6">
          <form
            className="grid gap-6"
            onSubmit={(event) => {
              event.preventDefault();
              handleSubmit();
            }}
          >
            <div className="grid gap-2">
              <Label htmlFor="username">管理员账号</Label>
              <Input id="username" {...form.register("username")} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="password">登录密码</Label>
              <Input id="password" type="password" {...form.register("password")} />
            </div>
            <div className="grid gap-4 rounded-2xl border border-stone-200 bg-stone-50 p-4">
              <div className="text-sm font-semibold text-stone-800">首个 Provider</div>
              <div className="grid gap-2">
                <Label htmlFor="provider-label">Provider 名称</Label>
                <Input id="provider-label" {...form.register("provider.label")} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="provider-base-url">Base URL</Label>
                <Input id="provider-base-url" {...form.register("provider.base_url")} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="provider-api-key">API Key</Label>
                <Input id="provider-api-key" type="password" {...form.register("provider.api_key")} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="provider-default-model">默认模型</Label>
                <Input id="provider-default-model" {...form.register("provider.default_model")} />
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>
              完成初始化
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
