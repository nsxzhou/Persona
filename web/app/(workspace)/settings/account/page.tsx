"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { AccountPanel } from "@/components/account-panel";
import { PageError, PageLoading } from "@/components/page-state";
import { api } from "@/lib/api";

export default function AccountPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const userQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: api.getCurrentUser,
  });

  const logoutMutation = useMutation({
    mutationFn: api.logout,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      router.replace("/login");
    },
  });

  if (userQuery.isLoading) {
    return <PageLoading />;
  }

  if (userQuery.isError || !userQuery.data) {
    return <PageError title="账户信息加载失败" message={userQuery.error instanceof Error ? userQuery.error.message : "请重试"} />;
  }

  return (
    <div className="space-y-4">
      {logoutMutation.isError ? (
        <PageError title="退出失败" message={logoutMutation.error instanceof Error ? logoutMutation.error.message : "请重试"} />
      ) : null}
      <AccountPanel submitting={logoutMutation.isPending} user={userQuery.data} onLogout={() => logoutMutation.mutateAsync()} />
    </div>
  );
}

