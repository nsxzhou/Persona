"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { ProjectForm } from "@/components/project-form";
import { api } from "@/lib/api";
import type { ProjectPayload } from "@/lib/types";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });
  const providersQuery = useQuery({
    queryKey: ["provider-configs"],
    queryFn: api.getProviderConfigs,
  });
  const mutation = useMutation({
    mutationFn: (payload: Partial<ProjectPayload>) => api.updateProject(projectId, payload),
    onError: (error) => toast.error(`保存失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("项目配置已保存");
      await projectQuery.refetch();
    },
  });

  if (projectQuery.isLoading || providersQuery.isLoading) {
    return <PageLoading />;
  }

  if (projectQuery.isError || providersQuery.isError || !projectQuery.data || !providersQuery.data) {
    return (
      <PageError
        title="项目详情加载失败"
        message={
          (projectQuery.error instanceof Error && projectQuery.error.message) ||
          (providersQuery.error instanceof Error && providersQuery.error.message) ||
          "请重试"
        }
      />
    );
  }

  const providers = providersQuery.data;

  return (
    <div className="space-y-4">
      <ProjectForm
        description="更新项目基本信息、默认模型与未来的 Style Profile 挂载入口。"
        project={projectQuery.data}
        providers={providers}
        submitting={mutation.isPending}
        title={projectQuery.data.name}
        onSubmit={async (values) => {
          await mutation.mutateAsync(values as Partial<ProjectPayload>);
        }}
      />
    </div>
  );
}
