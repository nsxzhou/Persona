"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { PageError } from "@/components/page-state";
import { PublicRouteGuard } from "@/components/route-guards";
import { SetupPageView } from "@/components/setup-page-view";
import { api } from "@/lib/api";
import type { SetupPayload } from "@/lib/types";

export default function SetupPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: SetupPayload) => api.setup(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["setup-status"] });
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      router.replace("/projects");
    },
  });

  return (
    <PublicRouteGuard>
      {mutation.isError ? (
        <PageError title="初始化失败" message={mutation.error instanceof Error ? mutation.error.message : "请重试"} />
      ) : null}
      <SetupPageView
        onSubmit={async (values) => {
          await mutation.mutateAsync(values);
        }}
        submitting={mutation.isPending}
      />
    </PublicRouteGuard>
  );
}
