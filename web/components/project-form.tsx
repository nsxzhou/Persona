"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";

import { Check, ChevronRight, ChevronsUpDown } from "lucide-react";

import { PageError, PageLoading } from "@/components/page-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Project, ProjectPayload, ProviderConfig, StyleProfileListItem } from "@/lib/types";

const schema = z.object({
  name: z.string().min(1),
  description: z.string(),
  status: z.enum(["draft", "active", "paused"]),
  default_provider_id: z.string().min(1),
  default_model: z.string().optional(),
  style_profile_id: z.string().nullable(),
});

type FormValues = z.infer<typeof schema>;

function useProjectFormPageData(projectId?: string) {
  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId as string),
    enabled: Boolean(projectId),
  });
  const providersQuery = useQuery({
    queryKey: ["provider-configs"],
    queryFn: api.getProviderConfigs,
  });
  const styleProfilesQuery = useQuery({
    queryKey: ["style-profiles"],
    queryFn: () => api.getStyleProfiles(),
  });

  const needsProject = Boolean(projectId);
  const isLoading =
    providersQuery.isLoading ||
    styleProfilesQuery.isLoading ||
    (needsProject && projectQuery.isLoading);
  const hasError =
    providersQuery.isError ||
    styleProfilesQuery.isError ||
    (needsProject && projectQuery.isError) ||
    !providersQuery.data ||
    !styleProfilesQuery.data ||
    (needsProject && !projectQuery.data);
  const errorMessage =
    (providersQuery.error instanceof Error && providersQuery.error.message) ||
    (styleProfilesQuery.error instanceof Error && styleProfilesQuery.error.message) ||
    (projectQuery.error instanceof Error && projectQuery.error.message) ||
    "请重试";

  return {
    isLoading,
    hasError,
    errorMessage,
    providers: providersQuery.data ?? [],
    styleProfiles: styleProfilesQuery.data ?? [],
    project: projectQuery.data,
    refetchProject: projectQuery.refetch,
  };
}

export function ProjectForm({
  providers,
  styleProfiles,
  project,
  submitting,
  onSubmit,
}: {
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  project?: Project;
  submitting: boolean;
  onSubmit: (values: ProjectPayload | Partial<ProjectPayload>) => Promise<void>;
}) {
  const [providerOpen, setProviderOpen] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema, undefined, { mode: "sync" }),
    defaultValues: {
      name: "",
      description: "",
      status: "draft",
      default_provider_id: "",
      default_model: "",
      style_profile_id: null,
    },
  });

  useEffect(() => {
    form.reset({
      name: project?.name ?? "",
      description: project?.description ?? "",
      status: project?.status ?? "draft",
      default_provider_id: project?.provider.id ?? providers[0]?.id ?? "",
      default_model: project?.default_model ?? "",
      style_profile_id: project?.style_profile_id ?? null,
    });
  }, [form, project]);

  return (
    <form
      onSubmit={form.handleSubmit(async (values) => {
        await onSubmit(values);
      })}
    >
      <Card>
        <CardContent className="grid gap-5 pt-6">
          <div className="grid gap-2">
            <Label htmlFor="project-name">项目名称</Label>
            <Input id="project-name" {...form.register("name")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-description">简介</Label>
            <Textarea id="project-description" className="min-h-[120px]" {...form.register("description")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-status">状态</Label>
            <Select
              value={form.watch("status")}
              onValueChange={(val) => form.setValue("status", val as "draft" | "active" | "paused")}
            >
              <SelectTrigger id="project-status" className="bg-background">
                <SelectValue placeholder="选择状态" />
              </SelectTrigger>
              <SelectContent className="border shadow-md rounded-md bg-popover text-popover-foreground">
                <SelectItem value="draft" className="cursor-pointer">draft</SelectItem>
                <SelectItem value="active" className="cursor-pointer">active</SelectItem>
                <SelectItem value="paused" className="cursor-pointer">paused</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-provider">默认 Provider</Label>
            <Popover open={providerOpen} onOpenChange={setProviderOpen}>
              <PopoverTrigger asChild>
                <Button
                  id="project-provider"
                  variant="outline"
                  role="combobox"
                  className="w-full justify-between font-normal bg-background hover:bg-accent hover:text-accent-foreground data-[state=open]:bg-accent h-10 px-3 py-2 text-sm border-input"
                >
                  <span className="truncate">
                    {form.watch("default_provider_id")
                      ? (() => {
                          const selected = providers.find((p) => p.id === form.watch("default_provider_id"));
                          return selected ? `${selected.label} / ${selected.default_model}` : "选择 Provider";
                        })()
                      : "选择 Provider"}
                  </span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50 transition-transform duration-200" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-full p-0 border shadow-md rounded-md" align="start" style={{ width: "var(--radix-popover-trigger-width)" }}>
                <Command className="bg-popover text-popover-foreground">
                  <CommandInput placeholder="搜索 Provider..." className="border-none focus:ring-0" />
                  <CommandList>
                    <CommandEmpty>未找到对应的 Provider</CommandEmpty>
                    <CommandGroup>
                      {providers.map((provider) => (
                        <CommandItem
                          key={provider.id}
                          value={`${provider.label} ${provider.default_model}`}
                          onSelect={() => {
                            form.setValue("default_provider_id", provider.id);
                            setProviderOpen(false);
                          }}
                          className="cursor-pointer"
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              form.watch("default_provider_id") === provider.id ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {provider.label}
                          <span className="ml-2 text-foreground/70 truncate">/ {provider.default_model}</span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-model">项目默认模型</Label>
            <Input id="project-model" placeholder="留空则回退到 Provider 默认模型" {...form.register("default_model")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-style-profile">风格档案</Label>
            <Select
              value={form.watch("style_profile_id") ?? "__none__"}
              onValueChange={(val) => form.setValue("style_profile_id", val === "__none__" ? null : val)}
            >
              <SelectTrigger id="project-style-profile" aria-label="风格档案" className="bg-background">
                <SelectValue placeholder="选择风格档案" />
              </SelectTrigger>
              <SelectContent className="border shadow-md rounded-md bg-popover text-popover-foreground">
                <SelectItem value="__none__" className="cursor-pointer">未挂载</SelectItem>
                {styleProfiles.map((profile) => (
                  <SelectItem key={profile.id} value={profile.id} className="cursor-pointer">
                    {profile.style_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3 mt-6 pt-6 border-t">
        <Button asChild variant="outline">
          <Link href="/projects">取消</Link>
        </Button>
        <Button type="submit" disabled={submitting}>
          保存项目
        </Button>
      </div>
    </form>
  );
}

export function ProjectNewPageClient() {
  const router = useRouter();
  const formData = useProjectFormPageData();
  const mutation = useMutation({
    mutationFn: (payload: ProjectPayload) => api.createProject(payload),
    onError: (error) => toast.error(`项目创建失败: ${error.message}`),
    onSuccess: (project) => {
      toast.success("项目创建成功");
      router.replace(`/projects/${project.id}`);
    },
  });

  if (formData.isLoading) {
    return <PageLoading />;
  }

  if (formData.hasError) {
    return (
      <PageError
        title="无法加载项目配置数据"
        message={formData.errorMessage}
      />
    );
  }

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
        providers={formData.providers}
        styleProfiles={formData.styleProfiles}
        submitting={mutation.isPending}
        onSubmit={async (values) => {
          await mutation.mutateAsync(values as ProjectPayload);
        }}
      />
    </div>
  );
}

export function ProjectDetailPageClient({ projectId }: { projectId: string }) {
  const formData = useProjectFormPageData(projectId);
  const mutation = useMutation({
    mutationFn: (payload: Partial<ProjectPayload>) =>
      api.updateProject(projectId, payload),
    onError: (error) => toast.error(`保存失败: ${error.message}`),
    onSuccess: async () => {
      toast.success("项目配置已保存");
      await formData.refetchProject();
    },
  });

  if (formData.isLoading) {
    return <PageLoading />;
  }

  if (formData.hasError || !formData.project) {
    return (
      <PageError
        title="项目详情加载失败"
        message={formData.errorMessage}
      />
    );
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center text-sm text-muted-foreground">
        <Link href="/projects" className="hover:text-foreground transition-colors">
          项目管理
        </Link>
        <ChevronRight className="h-4 w-4 mx-1" />
        <span className="text-foreground font-medium">{formData.project.name}</span>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{formData.project.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            更新项目基本信息、默认模型与未来的 Style Profile 挂载入口。
          </p>
        </div>
      </div>

      <ProjectForm
        project={formData.project}
        providers={formData.providers}
        styleProfiles={formData.styleProfiles}
        submitting={mutation.isPending}
        onSubmit={async (values) => {
          await mutation.mutateAsync(values as Partial<ProjectPayload>);
        }}
      />
    </div>
  );
}
