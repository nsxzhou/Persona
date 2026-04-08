"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { PublicRouteGuard } from "@/components/route-guards";
import { SetupPageView } from "@/components/setup-page-view";
import { api } from "@/lib/api";
import type { SetupPayload } from "@/lib/types";

export default function SetupPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: SetupPayload) => api.setup(payload),
    onError: (error) => toast.error(`初始化失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("系统初始化成功");
      await queryClient.invalidateQueries({ queryKey: ["setup-status"] });
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      router.replace("/projects");
    },
  });

  return (
    <PublicRouteGuard>
      <SetupPageView
        onSubmit={async (values) => {
          await mutation.mutateAsync(values);
        }}
        submitting={mutation.isPending}
      />
    </PublicRouteGuard>
  );
}
