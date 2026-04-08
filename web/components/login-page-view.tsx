"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Sparkles, User as UserIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { LoginPayload } from "@/lib/types";

const schema = z.object({
  username: z.string().min(3, "请输入有效的账号"),
  password: z.string().min(8, "密码最少8位"),
});

type FormValues = z.infer<typeof schema>;

export function LoginPageView({
  onSubmit,
  submitting,
}: {
  onSubmit: (values: LoginPayload) => Promise<void> | void;
  submitting: boolean;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema, undefined, { mode: "sync" }),
    defaultValues: {
      username: "",
      password: "",
    },
  });

  const handleSubmit = () => {
    const values = schema.parse(form.getValues());
    void onSubmit(values);
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/30 p-6 md:p-24">
      <div className="flex w-full max-w-md flex-col items-center gap-6">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
          <Sparkles className="h-8 w-8" />
        </div>
        
        <Card className="w-full shadow-lg border-muted">
          <CardHeader className="space-y-2 text-center">
            <CardTitle className="text-2xl font-bold tracking-tight">欢迎回来</CardTitle>
            <CardDescription className="text-muted-foreground">
              请输入您的管理员账号以进入工作台
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="grid gap-5"
              onSubmit={(event) => {
                event.preventDefault();
                handleSubmit();
              }}
            >
              <div className="grid gap-2">
                <Label htmlFor="login-username">管理员账号</Label>
                <div className="relative">
                  <UserIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input 
                    id="login-username" 
                    className="pl-9" 
                    {...form.register("username")} 
                    placeholder="输入账号"
                  />
                </div>
                {form.formState.errors.username && (
                  <p className="text-sm text-destructive">{form.formState.errors.username.message}</p>
                )}
              </div>
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="login-password">登录密码</Label>
                </div>
                <Input 
                  id="login-password" 
                  type="password" 
                  {...form.register("password")} 
                  placeholder="输入密码"
                />
                {form.formState.errors.password && (
                  <p className="text-sm text-destructive">{form.formState.errors.password.message}</p>
                )}
              </div>
              <Button type="submit" className="w-full mt-2" disabled={submitting}>
                {submitting ? "登录中..." : "进入工作台"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}