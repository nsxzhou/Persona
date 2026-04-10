"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronRight } from "lucide-react";
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
  const styleProfilesQuery = useQuery({
    queryKey: ["style-profiles"],
    queryFn: () => api.getStyleProfiles(),
  });
  const mutation = useMutation({
    mutationFn: (payload: Partial<ProjectPayload>) => api.updateProject(projectId, payload),
    onError: (error) => toast.error(`保存失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("项目配置已保存");
      await projectQuery.refetch();
    },
  });

  if (projectQuery.isLoading || providersQuery.isLoading || styleProfilesQuery.isLoading) {
    return <PageLoading />;
  }

  if (
    projectQuery.isError ||
    providersQuery.isError ||
    styleProfilesQuery.isError ||
    !projectQuery.data ||
    !providersQuery.data ||
    !styleProfilesQuery.data
  ) {
    return (
      <PageError
        title="项目详情加载失败"
        message={
          (projectQuery.error instanceof Error && projectQuery.error.message) ||
          (providersQuery.error instanceof Error && providersQuery.error.message) ||
          (styleProfilesQuery.error instanceof Error && styleProfilesQuery.error.message) ||
          "请重试"
        }
      />
    );
  }

  const providers = providersQuery.data;
  const styleProfiles = styleProfilesQuery.data;

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center text-sm text-muted-foreground">
        <Link href="/projects" className="hover:text-foreground transition-colors">
          项目管理
        </Link>
        <ChevronRight className="h-4 w-4 mx-1" />
        <span className="text-foreground font-medium">{projectQuery.data.name}</span>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{projectQuery.data.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            更新项目基本信息、默认模型与未来的 Style Profile 挂载入口。
          </p>
        </div>
      </div>

      <ProjectForm
        project={projectQuery.data}
        providers={providers}
        styleProfiles={styleProfiles}
        submitting={mutation.isPending}
        onSubmit={async (values) => {
          await mutation.mutateAsync(values as Partial<ProjectPayload>);
        }}
      />
    </div>
  );
}
