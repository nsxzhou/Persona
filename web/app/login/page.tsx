"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { LoginPageView } from "@/components/login-page-view";
import { PageError } from "@/components/page-state";
import { PublicRouteGuard } from "@/components/route-guards";
import { api } from "@/lib/api";
import type { LoginPayload } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: LoginPayload) => api.login(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      router.replace("/projects");
    },
  });

  return (
    <PublicRouteGuard>
      {mutation.isError ? (
        <PageError title="登录失败" message={mutation.error instanceof Error ? mutation.error.message : "请重试"} />
      ) : null}
      <LoginPageView
        onSubmit={async (values) => {
          await mutation.mutateAsync(values);
        }}
        submitting={mutation.isPending}
      />
    </PublicRouteGuard>
  );
}
