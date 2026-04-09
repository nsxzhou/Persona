"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight } from "lucide-react";
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
  const styleProfilesQuery = useQuery({
    queryKey: ["style-profiles"],
    queryFn: api.getStyleProfiles,
  });
  const mutation = useMutation({
    mutationFn: (payload: ProjectPayload) => api.createProject(payload),
    onError: (error) => toast.error(`项目创建失败: ${error.message}`),
    onSuccess: (project) => {
      toast.success("项目创建成功");
      router.replace(`/projects/${project.id}`);
    },
  });

  if (providersQuery.isLoading || styleProfilesQuery.isLoading) {
    return <PageLoading />;
  }

  if (
    providersQuery.isError ||
    styleProfilesQuery.isError ||
    !providersQuery.data ||
    !styleProfilesQuery.data
  ) {
    return (
      <PageError
        title="无法加载项目配置数据"
        message={
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
        <span className="text-foreground font-medium">新建项目</span>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">新建项目</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            先定义项目本身，再在下一阶段接入 Style Profile 和编辑器。
          </p>
        </div>
      </div>

      <ProjectForm
        providers={providers}
        styleProfiles={styleProfiles}
        submitting={mutation.isPending}
        onSubmit={async (values) => {
          await mutation.mutateAsync(values as ProjectPayload);
        }}
      />
    </div>
  );
}
