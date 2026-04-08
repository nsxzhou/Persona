"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { LoginPayload } from "@/lib/types";

const schema = z.object({
  username: z.string().min(3),
  password: z.string().min(8),
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
    <div className="mx-auto max-w-xl px-6 py-20">
      <Card>
        <CardHeader>
          <CardTitle>登录 Persona</CardTitle>
          <CardDescription>使用初始化时创建的管理员账号进入工作台。</CardDescription>
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
              <Input id="login-username" {...form.register("username")} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="login-password">登录密码</Label>
              <Input id="login-password" type="password" {...form.register("password")} />
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>
              登录 Persona
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
