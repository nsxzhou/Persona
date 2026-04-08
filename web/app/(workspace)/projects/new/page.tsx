"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { ProjectForm } from "@/components/project-form";
import { api } from "@/lib/api";
import type { ProjectPayload } from "@/lib/types";

export default function NewProjectPage() {
  const router = useRouter();
  const providersQuery = useQuery({
    queryKey: ["provider-configs"],
    queryFn: api.getProviderConfigs,
  });
  const mutation = useMutation({
    mutationFn: (payload: ProjectPayload) => api.createProject(payload),
    onError: (error) => toast.error(`项目创建失败: ${error.message}`),
    onSuccess: (project) => {
      toast.success("项目创建成功");
      router.replace(`/projects/${project.id}`);
    },
  });

  if (providersQuery.isLoading) {
    return <PageLoading />;
  }

  if (providersQuery.isError || !providersQuery.data) {
    return <PageError title="无法加载 Provider" message={providersQuery.error instanceof Error ? providersQuery.error.message : "请重试"} />;
  }

  const providers = providersQuery.data;

  return (
    <div className="space-y-4">
      <ProjectForm
        description="先定义项目本身，再在下一阶段接入 Style Profile 和编辑器。"
        providers={providers}
        submitting={mutation.isPending}
        title="新建项目"
        onSubmit={async (values) => {
          await mutation.mutateAsync(values as ProjectPayload);
        }}
      />
    </div>
  );
}
