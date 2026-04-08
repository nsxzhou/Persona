"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

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
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const restoreMutation = useMutation({
    mutationFn: (projectId: string) => api.restoreProject(projectId),
    onSuccess: async () => {
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
