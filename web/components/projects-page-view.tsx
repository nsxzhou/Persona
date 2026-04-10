"use client";

import Link from "next/link";
import { Plus, ArchiveRestore, Archive } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import type { Project } from "@/lib/types";

export function ProjectsPageView({
  projects,
  includeArchived,
  onIncludeArchivedChange,
  onArchive,
  onRestore,
}: {
  projects: Project[];
  includeArchived: boolean;
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

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {projects.length === 0 ? (
          <Card className="col-span-full">
            <CardHeader>
              <CardTitle>还没有项目</CardTitle>
              <CardDescription>先创建一个写作项目，后续再接入 Style Profile 和编辑器。</CardDescription>
            </CardHeader>
          </Card>
        ) : null}
        {projects.map((project) => (
          <Card key={project.id} className="flex flex-col transition-all hover:ring-2 hover:ring-primary hover:border-transparent cursor-pointer overflow-hidden">
            <CardHeader className="pb-4">
              <div className="flex items-start justify-between gap-4">
                <CardTitle className="text-lg leading-tight hover:underline line-clamp-1">
                  <Link href={`/projects/${project.id}`}>
                    {project.name}
                  </Link>
                </CardTitle>
                {project.archived_at ? (
                  <Badge variant="outline" className="bg-amber-100 text-amber-800 border-amber-200 shrink-0">已归档</Badge>
                ) : (
                  <Badge variant="secondary" className="shrink-0">{project.status || "草稿"}</Badge>
                )}
              </div>
              <CardDescription className="line-clamp-2 mt-2 min-h-[40px]">
                {project.description}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 pb-4">
              <div className="flex flex-col gap-2 text-xs text-muted-foreground bg-muted/50 rounded-md p-3">
                <div className="flex justify-between">
                  <span>提供方</span>
                  <strong className="font-medium text-foreground">{project.provider.label}</strong>
                </div>
                <div className="flex justify-between">
                  <span>模型</span>
                  <strong className="font-medium text-foreground truncate max-w-[120px] text-right" title={project.default_model}>{project.default_model}</strong>
                </div>
                <div className="flex justify-between">
                  <span>风格档案</span>
                  <strong className="font-medium text-foreground truncate max-w-[120px] text-right" title={project.style_profile_id ?? "未挂载"}>{project.style_profile_id ?? "未挂载"}</strong>
                </div>
              </div>
            </CardContent>
            <CardFooter className="pt-4 border-t flex gap-2 justify-end bg-muted/20">
              {project.archived_at ? (
                <Button variant="outline" size="sm" onClick={() => onRestore?.(project.id)}>
                  <ArchiveRestore className="mr-2 h-4 w-4" />
                  恢复
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={() => onArchive?.(project.id)}>
                  <Archive className="mr-2 h-4 w-4" />
                  归档
                </Button>
              )}
              <Button variant="secondary" size="sm" asChild>
                <Link href={`/projects/${project.id}`}>查看详情</Link>
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </section>
  );
}