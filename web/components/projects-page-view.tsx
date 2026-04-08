"use client";

import Link from "next/link";
import { Plus, ArchiveRestore, Archive } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-sm uppercase tracking-[0.24em] text-stone-400">Projects</div>
          <h1 className="mt-2 text-3xl font-semibold">项目管理</h1>
          <p className="mt-2 max-w-2xl text-sm text-stone-500">管理当前创作项目，并为每个项目绑定默认模型配置与后续风格档案入口。</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input
              aria-label="显示已归档项目"
              checked={includeArchived}
              className="h-4 w-4 rounded border-stone-300"
              type="checkbox"
              onChange={(event) => onIncludeArchivedChange(event.target.checked)}
            />
            显示已归档项目
          </label>
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
          <Card key={project.id}>
            <CardContent className="flex flex-col gap-4 py-6 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Link href={`/projects/${project.id}`} className="text-xl font-semibold text-stone-900 hover:text-stone-700">
                    {project.name}
                  </Link>
                  <Badge>{project.status}</Badge>
                  {project.archived_at ? <Badge className="bg-amber-100 text-amber-700">archived</Badge> : null}
                </div>
                <p className="text-sm text-stone-500">{project.description}</p>
                <div className="flex flex-wrap gap-3 text-xs text-stone-500">
                  <span>Provider: {project.provider.label}</span>
                  <span>Model: {project.default_model}</span>
                  <span>Style Profile: {project.style_profile_id ?? "未挂载"}</span>
                </div>
              </div>
              <div className="flex gap-2">
                {project.archived_at ? (
                  <Button variant="outline" onClick={() => onRestore?.(project.id)}>
                    <ArchiveRestore className="mr-2 h-4 w-4" />
                    恢复
                  </Button>
                ) : (
                  <Button variant="outline" onClick={() => onArchive?.(project.id)}>
                    <Archive className="mr-2 h-4 w-4" />
                    归档
                  </Button>
                )}
                <Button asChild variant="secondary">
                  <Link href={`/projects/${project.id}`}>查看详情</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

