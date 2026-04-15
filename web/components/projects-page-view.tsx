"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Plus, ArchiveRestore, Archive, PenLine } from "lucide-react";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";

const PAGE_SIZE = 10;

export function ProjectsPageClient() {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();
  
  const projectsQuery = useQuery({
    queryKey: ["projects", includeArchived, page],
    queryFn: () => api.getProjects({ 
      includeArchived, 
      offset: (page - 1) * PAGE_SIZE, 
      limit: PAGE_SIZE 
    }),
  });

  const archiveMutation = useMutation({
    mutationFn: (projectId: string) => api.archiveProject(projectId),
    onError: (error) => toast.error(error.message),
    onSuccess: async () => {
      toast.success("项目已归档");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const restoreMutation = useMutation({
    mutationFn: (projectId: string) => api.restoreProject(projectId),
    onError: (error) => toast.error(error.message),
    onSuccess: async () => {
      toast.success("项目已恢复");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  if (projectsQuery.isLoading) {
    return <PageLoading />;
  }

  if (projectsQuery.isError || !projectsQuery.data) {
    return (
      <PageError
        title="项目列表加载失败"
        message={projectsQuery.error instanceof Error ? projectsQuery.error.message : "请重试"}
      />
    );
  }

  return (
    <ProjectsPageView
      includeArchived={includeArchived}
      projects={projectsQuery.data}
      page={page}
      hasNextPage={projectsQuery.data.length === PAGE_SIZE}
      onPageChange={setPage}
      onArchive={(projectId) => archiveMutation.mutate(projectId)}
      onIncludeArchivedChange={(checked) => {
        setIncludeArchived(checked);
        setPage(1); // Reset page on filter change
      }}
      onRestore={(projectId) => restoreMutation.mutate(projectId)}
    />
  );
}

export function ProjectsPageView({
  projects,
  includeArchived,
  page,
  hasNextPage,
  onPageChange,
  onIncludeArchivedChange,
  onArchive,
  onRestore,
}: {
  projects: Project[];
  includeArchived: boolean;
  page: number;
  hasNextPage: boolean;
  onPageChange: (page: number) => void;
  onIncludeArchivedChange: (checked: boolean) => void;
  onArchive?: (id: string) => void;
  onRestore?: (id: string) => void;
}) {
  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">项目管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            管理当前创作项目，并为每个项目绑定默认模型配置与后续风格档案入口。
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center space-x-2 text-muted-foreground">
            <Switch
              id="include-archived"
              checked={includeArchived}
              onCheckedChange={onIncludeArchivedChange}
            />
            <Label htmlFor="include-archived">
              显示已归档
            </Label>
          </div>
          <Button asChild>
            <Link href="/projects/new">
              <Plus className="mr-2 h-4 w-4" />
              新建项目
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4">
        {projects.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>还没有项目</CardTitle>
              <CardDescription>先创建一个写作项目，后续再接入 Style Profile 和编辑器。</CardDescription>
            </CardHeader>
          </Card>
        ) : null}
        {projects.map((project) => (
          <div key={project.id} className="rounded-xl border border-border bg-card text-card-foreground shadow-sm transition-all hover:ring-2 hover:ring-primary hover:border-transparent cursor-pointer">
            <div className="flex flex-col gap-4 p-6 lg:flex-row lg:items-center justify-between">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <Link href={`/projects/${project.id}`} className="text-lg font-semibold leading-none tracking-tight hover:underline">
                    {project.name}
                  </Link>
                  {project.archived_at ? (
                    <Badge variant="outline" className="bg-amber-100 text-amber-800 border-amber-200">已归档</Badge>
                  ) : (
                    <Badge variant="secondary">{project.status || "草稿"}</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{project.description}</p>
                <div className="flex gap-3 pt-2 text-xs text-muted-foreground">
                  <span>提供方：<strong className="font-medium text-foreground">{project.provider.label}</strong></span>
                  <span>模型：<strong className="font-medium text-foreground">{project.default_model}</strong></span>
                  <span>风格档案：<strong className="font-medium text-foreground">{project.style_profile_id ?? "未挂载"}</strong></span>
                </div>
              </div>
              <div className="flex gap-2">
                {project.archived_at ? (
                  <Button variant="outline" onClick={() => onRestore?.(project.id)}>
                    <ArchiveRestore className="mr-2 h-4 w-4" />
                    恢复
                  </Button>
                ) : (
                  <>
                    <Button variant="outline" onClick={() => onArchive?.(project.id)}>
                      <Archive className="mr-2 h-4 w-4" />
                      归档
                    </Button>
                    <Button asChild className="gap-2">
                      <Link href={`/projects/${project.id}/editor`}>
                        <PenLine className="h-4 w-4" />
                        开始写作
                      </Link>
                    </Button>
                  </>
                )}
                <Button variant="secondary" asChild>
                  <Link href={`/projects/${project.id}`}>查看详情</Link>
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination (Standard) */}
      {projects.length > 0 || page > 1 ? (
        <Pagination className="mt-8 justify-end">
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious 
                href="#" 
                onClick={(e) => {
                  e.preventDefault();
                  if (page > 1) onPageChange(page - 1);
                }}
                className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
              />
            </PaginationItem>
            
            <PaginationItem>
              <PaginationLink 
                href="#" 
                onClick={(e) => e.preventDefault()}
                isActive
              >
                {page}
              </PaginationLink>
            </PaginationItem>
            
            <PaginationItem>
              <PaginationNext 
                href="#" 
                onClick={(e) => {
                  e.preventDefault();
                  if (hasNextPage) onPageChange(page + 1);
                }}
                className={!hasNextPage ? "pointer-events-none opacity-50" : "cursor-pointer"}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      ) : null}
    </section>
  );
}
