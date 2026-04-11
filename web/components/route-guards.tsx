"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { LoginPageView } from "@/components/login-page-view";
import { SetupPageView } from "@/components/setup-page-view";
import type { LoginPayload, SetupPayload } from "@/lib/types";

export function SetupPageClient() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: SetupPayload) => api.setup(payload),
    onError: (error) => toast.error(error.message),
    onSuccess: async () => {
      toast.success("系统初始化成功");
      await queryClient.invalidateQueries({ queryKey: ["setup-status"] });
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      router.replace("/projects");
    },
  });

  return (
    <SetupPageView
      onSubmit={async (values) => {
        await mutation.mutateAsync(values);
      }}
      submitting={mutation.isPending}
    />
  );
}

export function LoginPageClient() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: LoginPayload) => api.login(payload),
    onError: (error) => toast.error(error.message),
    onSuccess: async () => {
      toast.success("登录成功");
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      router.replace("/projects");
    },
  });

  return (
    <LoginPageView
      onSubmit={async (values) => {
        await mutation.mutateAsync(values);
      }}
      submitting={mutation.isPending}
    />
  );
}
