"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ChevronRight as Breadcrumb,
  PenLine,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import { useDebounceSave } from "@/hooks/use-debounce-save";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProjectBootstrapDialog } from "@/components/project-bootstrap-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { WorkbenchTabs } from "@/components/workbench-tabs";
import { updateProjectAction } from "@/app/(workspace)/projects/actions";
import { api } from "@/lib/api";
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
  const router = useRouter();
  const [displayName, setDisplayName] = useState(initialProject.name);
  const [status, setStatus] = useState(initialProject.status);
  const [activeTab, setActiveTab] = useState(initialTab);
  const [bootstrapRunId, setBootstrapRunId] = useState<string | null>(null);
  const [bootstrapBundle, setBootstrapBundle] = useState("");
  const [showBootstrapDialog, setShowBootstrapDialog] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(false);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const isBlankProjectBible = (bible: ProjectBible) =>
    !bible.world_building.trim()
    && !bible.characters_blueprint.trim()
    && !bible.outline_master.trim()
    && !bible.outline_detail.trim()
    && !bible.characters_status.trim()
    && !bible.runtime_state.trim()
    && !bible.runtime_threads.trim();

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

  const waitBootstrapToFinish = async (runId: string) => {
    const status = await api.waitForNovelWorkflow(runId);
    if (status.status === "failed") {
      throw new Error(status.error_message || "项目初始化失败");
    }
    if (status.status === "paused") {
      throw new Error("项目初始化仍处于暂停状态，请在审核对话框中继续");
    }
    toast.success("项目初始化完成");
    router.refresh();
  };

  const handleProjectBootstrap = async () => {
    if (isBootstrapping) return;
    setIsBootstrapping(true);
    try {
      const latestBible = await api.getProjectBible(initialProject.id);
      if (!isBlankProjectBible(latestBible)) {
        toast.info("该项目已存在 Bible 内容，无法一键初始化");
        return;
      }

      const { run, status } = await api.runProjectBootstrapWorkflow(initialProject.id);
      setBootstrapRunId(run.id);

      if (status.status === "failed") {
        throw new Error(status.error_message || "项目初始化失败");
      }

      if (status.status === "paused" && status.checkpoint_kind === "outline_bundle") {
        const bundle = await api.getNovelWorkflowArtifact(run.id, "outline_bundle");
        setBootstrapBundle(bundle);
        setShowBootstrapDialog(true);
        return;
      }

      if (status.status === "succeeded") {
        toast.success("项目初始化完成");
        router.refresh();
        return;
      }

      throw new Error("项目初始化状态异常");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "项目初始化失败";
      toast.error(message);
    } finally {
      setIsBootstrapping(false);
    }
  };

  const handleBootstrapApprove = async () => {
    if (!bootstrapRunId || isBootstrapping) return;
    setIsBootstrapping(true);
    try {
      await api.decideNovelWorkflow(bootstrapRunId, {
        action: "approve",
        artifact_name: "outline_bundle",
      });
      setShowBootstrapDialog(false);
      await waitBootstrapToFinish(bootstrapRunId);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "提交失败";
      toast.error(message);
    } finally {
      setIsBootstrapping(false);
    }
  };

  const handleBootstrapRevise = async (editedMarkdown: string) => {
    if (!bootstrapRunId || isBootstrapping) return;
    setIsBootstrapping(true);
    try {
      await api.decideNovelWorkflow(bootstrapRunId, {
        action: "revise",
        artifact_name: "outline_bundle",
        edited_markdown: editedMarkdown,
      });
      setShowBootstrapDialog(false);
      await waitBootstrapToFinish(bootstrapRunId);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "提交失败";
      toast.error(message);
    } finally {
      setIsBootstrapping(false);
    }
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
        <div className="flex items-center gap-2 shrink-0 mt-1">
          <Button
            variant="outline"
            className="gap-2"
            disabled={isBootstrapping || !isBlankProjectBible(initialProjectBible)}
            onClick={handleProjectBootstrap}
          >
            <Wand2 className={`h-4 w-4 ${isBootstrapping ? "animate-spin" : ""}`} />
            一键初始化 (AI)
          </Button>
          <Button asChild className="gap-2">
            <Link href={`/projects/${initialProject.id}/editor`}>
              <PenLine className="h-4 w-4" />
              进入编辑器
            </Link>
          </Button>
        </div>
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

      <ProjectBootstrapDialog
        open={showBootstrapDialog}
        bundleMarkdown={bootstrapBundle}
        busy={isBootstrapping}
        onApprove={handleBootstrapApprove}
        onRevise={handleBootstrapRevise}
        onDismiss={() => setShowBootstrapDialog(false)}
      />
    </div>
  );
}
