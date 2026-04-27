"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ChevronRight as Breadcrumb,
  PenLine,
} from "lucide-react";
import { toast } from "sonner";
import { useDebounceSave } from "@/hooks/use-debounce-save";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { WorkbenchTabs } from "@/components/workbench-tabs";
import { updateProjectAction } from "@/app/(workspace)/projects/actions";
import type { PlotProfileListItem, Project, ProjectBible, ProviderConfig, StyleProfileListItem } from "@/lib/types";

export function ProjectWorkbench(props: {
  project: Project;
  projectBible: ProjectBible;
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  plotProfiles: PlotProfileListItem[];
  initialTab?: string;
  highlightedVolumeIndex?: number | null;
}) {
  return <ProjectWorkbenchInner key={props.project.id} {...props} />;
}

function ProjectWorkbenchInner({
  project: initialProject,
  projectBible: initialProjectBible,
  providers,
  styleProfiles,
  plotProfiles,
  initialTab = "description",
  highlightedVolumeIndex = null,
}: {
  project: Project;
  projectBible: ProjectBible;
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  plotProfiles: PlotProfileListItem[];
  initialTab?: string;
  highlightedVolumeIndex?: number | null;
}) {
  const [displayName, setDisplayName] = useState(initialProject.name);
  const [status, setStatus] = useState(initialProject.status);
  const [activeTab, setActiveTab] = useState(initialTab);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const debouncedSave = useDebounceSave(async (field: string, value: string) => {
    try {
      await updateProjectAction(initialProject.id, { [field]: value });
    } catch {
      toast.error(`保存 ${field === "name" ? "项目名称" : "状态"} 失败`);
    }
  }, 1000);

  const handleNameChange = (val: string) => {
    setDisplayName(val);
    debouncedSave("name", val);
  };

  const handleStatusChange = (val: "draft" | "active" | "paused") => {
    setStatus(val);
    debouncedSave("status", val);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center text-sm text-muted-foreground">
        <Link href="/projects" className="hover:text-foreground transition-colors">
          项目管理
        </Link>
        <Breadcrumb className="h-4 w-4 mx-1" />
        <span className="text-foreground font-medium">{displayName || "未命名项目"}</span>
      </div>

      {/* Title bar */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <input
            type="text"
            value={displayName}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="未命名项目..."
            className="text-3xl font-bold tracking-tight bg-transparent border-none outline-none focus:ring-0 p-0 placeholder:text-muted-foreground/30 w-full transition-colors"
          />
          <div className="flex items-center gap-3">
            <Select value={status} onValueChange={handleStatusChange}>
              <SelectTrigger className="h-7 w-fit gap-2 bg-muted/50 border-dashed hover:bg-muted transition-colors text-xs font-medium">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="draft">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="h-2 w-2 rounded-full p-0" />
                    <span>草稿 (Draft)</span>
                  </div>
                </SelectItem>
                <SelectItem value="active">
                  <div className="flex items-center gap-2">
                    <Badge variant="default" className="h-2 w-2 rounded-full p-0 bg-green-500" />
                    <span>进行中 (Active)</span>
                  </div>
                </SelectItem>
                <SelectItem value="paused">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="h-2 w-2 rounded-full p-0 bg-yellow-500" />
                    <span>已暂停 (Paused)</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              创作工作台 — 在这里构建你的小说世界，然后进入编辑器开始写作。
            </p>
          </div>
        </div>
        <Button asChild className="gap-2 shrink-0 mt-1">
          <Link href={`/projects/${initialProject.id}/editor`}>
            <PenLine className="h-4 w-4" />
            进入编辑器
          </Link>
        </Button>
      </div>

      {/* Tab-based workbench */}
      <WorkbenchTabs
        project={initialProject}
        projectBible={initialProjectBible}
        providers={providers}
        styleProfiles={styleProfiles}
        plotProfiles={plotProfiles}
        onNameChange={setDisplayName}
        activeTab={activeTab}
        onActiveTabChange={setActiveTab}
        highlightedVolumeIndex={highlightedVolumeIndex}
      />
    </div>
  );
}
