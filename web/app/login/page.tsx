"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { LoginPageView } from "@/components/login-page-view";
import { PublicRouteGuard } from "@/components/route-guards";
import { api } from "@/lib/api";
import type { LoginPayload } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: LoginPayload) => api.login(payload),
    onError: (error) => toast.error(`登录失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("登录成功");
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      router.replace("/projects");
    },
  });

  return (
    <PublicRouteGuard>
      <LoginPageView
        onSubmit={async (values) => {
          await mutation.mutateAsync(values);
        }}
        submitting={mutation.isPending}
      />
    </PublicRouteGuard>
  );
}
