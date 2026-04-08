"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { ProjectsPageView } from "@/components/projects-page-view";
import { api } from "@/lib/api";

export default function ProjectsPage() {
  const [includeArchived, setIncludeArchived] = useState(false);
  const queryClient = useQueryClient();
  const projectsQuery = useQuery({
    queryKey: ["projects", includeArchived],
    queryFn: () => api.getProjects(includeArchived),
  });

  const archiveMutation = useMutation({
    mutationFn: (projectId: string) => api.archiveProject(projectId),
    onError: (error) => toast.error(`归档失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("项目已归档");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const restoreMutation = useMutation({
    mutationFn: (projectId: string) => api.restoreProject(projectId),
    onError: (error) => toast.error(`恢复失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("项目已恢复");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  if (projectsQuery.isLoading) {
    return <PageLoading />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return <PageError title="项目列表加载失败" message={projectsQuery.error instanceof Error ? projectsQuery.error.message : "请重试"} />;
  }

  const projects = projectsQuery.data;

  return (
    <ProjectsPageView
      includeArchived={includeArchived}
      projects={projects}
      onArchive={(projectId) => archiveMutation.mutate(projectId)}
      onIncludeArchivedChange={setIncludeArchived}
      onRestore={(projectId) => restoreMutation.mutate(projectId)}
    />
  );
}
