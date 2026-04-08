"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Bot, ChevronRight, Server, ShieldCheck, Sparkles, User as UserIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { SetupPayload } from "@/lib/types";

const schema = z.object({
  username: z.string().min(3, "用户名至少需要 3 个字符"),
  password: z.string().min(8, "密码至少需要 8 个字符"),
  provider: z.object({
    label: z.string().min(1, "必填"),
    base_url: z.string().url("需为有效 URL").min(1),
    api_key: z.string().min(4, "必填"),
    default_model: z.string().min(1, "必填"),
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
  const [step, setStep] = useState<1 | 2>(1);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema, undefined, { mode: "sync" }),
    defaultValues: {
      username: "",
      password: "",
      provider: {
        label: "",
        base_url: "https://api.openai.com/v1",
        api_key: "",
        default_model: "gpt-4o-mini",
        is_enabled: true,
      },
    },
  });

  const handleNext = async () => {
    const isValid = await form.trigger(["username", "password"]);
    if (isValid) {
      setStep(2);
    }
  };

  const onFinalSubmit = (values: FormValues) => {
    const finalValues = {
      ...values,
      provider: {
        ...values.provider,
        is_enabled: true,
      },
    };
    void onSubmit(finalValues);
  };

  return (
    <div className="flex min-h-screen w-full bg-muted/30">
      {/* 左侧插画区 */}
      <div className="hidden w-1/2 flex-col justify-center bg-primary p-12 text-primary-foreground lg:flex">
        <div className="mx-auto max-w-md space-y-8">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <div className="space-y-4">
            <h1 className="text-4xl font-bold tracking-tight">欢迎来到 Persona</h1>
            <p className="text-lg text-primary-foreground/80 leading-relaxed">
              这是一个专属于您的私有化工作台。完成初始化后，您将能够接入任意兼容 OpenAI 协议的 Provider，开始打造您的智能体网络。
            </p>
          </div>
          <div className="grid gap-6 pt-8">
            <div className="flex items-center gap-4">
              <ShieldCheck className="h-6 w-6 text-primary-foreground/60" />
              <span className="text-sm font-medium">数据安全与本地化存储</span>
            </div>
            <div className="flex items-center gap-4">
              <Server className="h-6 w-6 text-primary-foreground/60" />
              <span className="text-sm font-medium">自由接入任何 Provider</span>
            </div>
            <div className="flex items-center gap-4">
              <Bot className="h-6 w-6 text-primary-foreground/60" />
              <span className="text-sm font-medium">高效管理多个智能项目</span>
            </div>
          </div>
        </div>
      </div>

      {/* 右侧表单区 */}
      <div className="flex flex-1 flex-col justify-center px-6 py-12 sm:px-12 lg:px-24">
        <div className="mx-auto w-full max-w-md space-y-8">
          <div className="space-y-2 lg:hidden">
            <h1 className="text-3xl font-bold">初始化 Persona</h1>
            <p className="text-muted-foreground">创建管理员账号，并接入首个 Provider。</p>
          </div>

          <Card className="border-0 shadow-none sm:border sm:shadow-sm">
            <CardHeader className="space-y-1">
              <CardTitle className="text-2xl">{step === 1 ? "创建管理员账号" : "配置首个 Provider"}</CardTitle>
              <CardDescription>
                {step === 1 ? "步骤 1 / 2" : "步骤 2 / 2"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form
                className="grid gap-6"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (step === 2) {
                    void form.handleSubmit(onFinalSubmit)(event);
                  }
                }}
              >
                {step === 1 && (
                  <div className="grid gap-4 animate-in fade-in slide-in-from-right-4 duration-300">
                    <div className="grid gap-2">
                      <Label htmlFor="username">管理员账号</Label>
                      <div className="relative">
                        <UserIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                        <Input id="username" className="pl-9" {...form.register("username")} placeholder="admin" />
                      </div>
                      {form.formState.errors.username && (
                        <p className="text-sm text-destructive">{form.formState.errors.username.message}</p>
                      )}
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="password">登录密码</Label>
                      <Input id="password" type="password" {...form.register("password")} placeholder="至少 8 个字符" />
                      {form.formState.errors.password && (
                        <p className="text-sm text-destructive">{form.formState.errors.password.message}</p>
                      )}
                    </div>
                    <Button type="button" className="w-full mt-4" onClick={handleNext}>
                      下一步
                      <ChevronRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                )}

                {step === 2 && (
                  <div className="grid gap-4 animate-in fade-in slide-in-from-right-4 duration-300">
                    <div className="grid gap-2">
                      <Label htmlFor="provider-label">Provider 名称</Label>
                      <Input id="provider-label" {...form.register("provider.label")} placeholder="例如：OpenAI" />
                      {form.formState.errors.provider?.label && (
                        <p className="text-sm text-destructive">{form.formState.errors.provider.label.message}</p>
                      )}
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="provider-base-url">Base URL</Label>
                      <Input id="provider-base-url" {...form.register("provider.base_url")} />
                      {form.formState.errors.provider?.base_url && (
                        <p className="text-sm text-destructive">{form.formState.errors.provider.base_url.message}</p>
                      )}
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="provider-api-key">API Key</Label>
                      <Input id="provider-api-key" type="password" {...form.register("provider.api_key")} placeholder="sk-..." />
                      {form.formState.errors.provider?.api_key && (
                        <p className="text-sm text-destructive">{form.formState.errors.provider.api_key.message}</p>
                      )}
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="provider-default-model">默认模型</Label>
                      <Input id="provider-default-model" {...form.register("provider.default_model")} />
                      {form.formState.errors.provider?.default_model && (
                        <p className="text-sm text-destructive">{form.formState.errors.provider.default_model.message}</p>
                      )}
                    </div>
                    <div className="flex gap-3 mt-4">
                      <Button type="button" variant="outline" className="w-1/3" onClick={() => setStep(1)}>
                        返回
                      </Button>
                      <Button type="submit" className="w-2/3" disabled={submitting}>
                        {submitting ? "初始化中..." : "完成初始化"}
                      </Button>
                    </div>
                  </div>
                )}
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
