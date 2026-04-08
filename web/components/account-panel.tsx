"use client";

import { useState } from "react";
import { LogOut, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
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
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await api.deleteAccount();
      queryClient.clear();
      router.replace("/setup");
    } catch (error) {
      console.error("Delete account failed:", error);
      setIsDeleting(false);
      setIsDialogOpen(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>账户信息</CardTitle>
        <CardDescription>当前应用只支持单用户工作模式，后续仍以本地化和私有化为主。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-2 text-sm text-muted-foreground">
          <div className="flex justify-between gap-3">
            <span>账号</span>
            <span className="font-medium text-foreground">{user.username}</span>
          </div>
          <div className="flex justify-between gap-3">
            <span>创建时间</span>
            <span className="font-medium text-foreground">{new Date(user.created_at).toLocaleString("zh-CN")}</span>
          </div>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button variant="outline" onClick={onLogout} disabled={submitting || isDeleting}>
            <LogOut className="mr-2 h-4 w-4" />
            退出登录
          </Button>

          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="destructive" disabled={submitting || isDeleting}>
                <Trash2 className="mr-2 h-4 w-4" />
                注销并重置系统
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>确认注销账号并重置系统？</DialogTitle>
                <DialogDescription>
                  此操作将不可逆地删除您的账号、所有 Provider 配置以及所有项目数据，系统将回到初始的未配置状态。
                </DialogDescription>
              </DialogHeader>
              <div className="mt-8 flex justify-end gap-3">
                <DialogClose asChild>
                  <Button variant="outline" disabled={isDeleting}>取消</Button>
                </DialogClose>
                <Button 
                  variant="destructive" 
                  onClick={handleDeleteAccount} 
                  disabled={isDeleting}
                >
                  {isDeleting ? "重置中..." : "确认重置"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </CardContent>
    </Card>
  );
}