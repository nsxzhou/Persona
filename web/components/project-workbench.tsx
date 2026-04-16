"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ChevronRight as Breadcrumb,
  PenLine,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { WorkbenchTabs } from "@/components/workbench-tabs";
import type { Project, ProviderConfig, StyleProfileListItem } from "@/lib/types";

export function ProjectWorkbench({
  project: initialProject,
  providers,
  styleProfiles,
  initialTab = "inspiration",
  highlightedVolumeIndex = null,
}: {
  project: Project;
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  initialTab?: string;
  highlightedVolumeIndex?: number | null;
}) {
  const [displayName, setDisplayName] = useState(initialProject.name);
  const [activeTab, setActiveTab] = useState(initialTab);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center text-sm text-muted-foreground">
        <Link href="/projects" className="hover:text-foreground transition-colors">
          项目管理
        </Link>
        <Breadcrumb className="h-4 w-4 mx-1" />
        <span className="text-foreground font-medium">{displayName}</span>
      </div>

      {/* Title bar */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{displayName}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            创作工作台 — 在这里构建你的小说世界，然后进入编辑器开始写作。
          </p>
        </div>
        <Button asChild className="gap-2">
          <Link href={`/projects/${initialProject.id}/editor`}>
            <PenLine className="h-4 w-4" />
            进入编辑器
          </Link>
        </Button>
      </div>

      {/* Tab-based workbench */}
      <WorkbenchTabs
        project={initialProject}
        providers={providers}
        styleProfiles={styleProfiles}
        onNameChange={setDisplayName}
        activeTab={activeTab}
        onActiveTabChange={setActiveTab}
        highlightedVolumeIndex={highlightedVolumeIndex}
      />
    </div>
  );
}
