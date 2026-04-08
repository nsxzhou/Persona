"use client";

import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { User } from "@/lib/types";

export function AccountPanel({
  user,
  onLogout,
  submitting,
}: {
  user: User;
  onLogout: () => Promise<void>;
  submitting: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>账户信息</CardTitle>
        <CardDescription>当前应用只支持单用户工作模式，后续仍以本地化和私有化为主。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 text-sm text-stone-600">
          <div className="flex justify-between gap-3">
            <span>账号</span>
            <span className="font-medium text-stone-900">{user.username}</span>
          </div>
          <div className="flex justify-between gap-3">
            <span>创建时间</span>
            <span className="font-medium text-stone-900">{new Date(user.created_at).toLocaleString("zh-CN")}</span>
          </div>
        </div>
        <Button variant="outline" onClick={onLogout} disabled={submitting}>
          <LogOut className="mr-2 h-4 w-4" />
          退出登录
        </Button>
      </CardContent>
    </Card>
  );
}

