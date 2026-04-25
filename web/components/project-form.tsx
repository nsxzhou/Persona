"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect, useMemo } from "react";
import { useForm, useWatch } from "react-hook-form";
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
import type {
  PlotProfileListItem,
  Project,
  ProjectPayload,
  ProviderConfig,
  StyleProfileListItem,
} from "@/lib/types";

import { createProjectAction, updateProjectAction } from "@/app/(workspace)/projects/actions";

const schema = z.object({
  name: z.string().min(1, { message: "项目名称不能为空" }),
  description: z.string(),
  status: z.enum(["draft", "active", "paused"]),
  default_provider_id: z.string().min(1, { message: "必须选择一个可用的默认 Provider" }),
  default_model: z.string().optional(),
  style_profile_id: z.string().nullable(),
  plot_profile_id: z.string().nullable(),
  generation_genre_mother: z.string().nullable(),
  generation_desire_overlays: z.string(),
  generation_intensity_level: z.string().nullable(),
  generation_pov_mode: z.string(),
  generation_morality_axis: z.string(),
  generation_pace_density: z.string(),
});

type FormValues = z.infer<typeof schema>;


export function ProjectForm({
  providers,
  styleProfiles,
  plotProfiles,
  project,
  submitting,
  onSubmit,
}: {
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  plotProfiles: PlotProfileListItem[];
  project?: Project;
  submitting: boolean;
  onSubmit: (values: ProjectPayload | Partial<ProjectPayload>) => Promise<void>;
}) {
  const enabledProviders = useMemo(() => providers.filter(p => p.is_enabled), [providers]);

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
      plot_profile_id: null,
      generation_genre_mother: null,
      generation_desire_overlays: "",
      generation_intensity_level: null,
      generation_pov_mode: "limited_third",
      generation_morality_axis: "gray_pragmatism",
      generation_pace_density: "balanced",
    },
  });

  useEffect(() => {
    form.reset({
      name: project?.name ?? "",
      description: project?.description ?? "",
      status: project?.status ?? "draft",
      default_provider_id: project?.provider?.id ?? enabledProviders[0]?.id ?? "",
      default_model: project?.default_model ?? "",
      style_profile_id: project?.style_profile_id ?? null,
      plot_profile_id: project?.plot_profile_id ?? null,
      generation_genre_mother: project?.generation_profile?.genre_mother ?? null,
      generation_desire_overlays: project?.generation_profile?.desire_overlays?.join(", ") ?? "",
      generation_intensity_level: project?.generation_profile?.intensity_level ?? null,
      generation_pov_mode: project?.generation_profile?.pov_mode ?? "limited_third",
      generation_morality_axis: project?.generation_profile?.morality_axis ?? "gray_pragmatism",
      generation_pace_density: project?.generation_profile?.pace_density ?? "balanced",
    });
  }, [form, project, enabledProviders]);

  const selectedStatus = useWatch({ control: form.control, name: "status" });
  const selectedProviderId = useWatch({ control: form.control, name: "default_provider_id" });
  const selectedStyleProfileId = useWatch({ control: form.control, name: "style_profile_id" });
  const selectedPlotProfileId = useWatch({ control: form.control, name: "plot_profile_id" });
  const selectedProvider = useMemo(
    () => providers.find((provider) => provider.id === selectedProviderId),
    [providers, selectedProviderId],
  );
  const selectedGenreMother = useWatch({ control: form.control, name: "generation_genre_mother" });
  const selectedIntensityLevel = useWatch({ control: form.control, name: "generation_intensity_level" });

  return (
    <form
      onSubmit={form.handleSubmit(
        async (values) => {
          const overlays = values.generation_desire_overlays
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);
          await onSubmit({
            name: values.name,
            description: values.description,
            status: values.status,
            default_provider_id: values.default_provider_id,
            default_model: values.default_model,
            style_profile_id: values.style_profile_id,
            plot_profile_id: values.plot_profile_id,
            generation_profile:
              values.generation_genre_mother && values.generation_intensity_level
                ? {
                    genre_mother: values.generation_genre_mother,
                    desire_overlays: overlays,
                    intensity_level: values.generation_intensity_level,
                    pov_mode: values.generation_pov_mode,
                    morality_axis: values.generation_morality_axis,
                    pace_density: values.generation_pace_density,
                  }
                : null,
          });
        },
        (errors) => {
          const firstError = Object.values(errors)[0];
          if (firstError?.message) {
            toast.error(firstError.message as string);
          }
        }
      )}
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
          <div className="grid gap-4 rounded-lg border p-4">
            <div className="text-sm font-medium">Generation Profile</div>
            <div className="grid gap-2">
              <Label htmlFor="generation-genre">题材母类</Label>
              <Select
                value={selectedGenreMother ?? "__none__"}
                onValueChange={(val) => form.setValue("generation_genre_mother", val === "__none__" ? null : val)}
              >
                <SelectTrigger id="generation-genre" aria-label="题材母类">
                  <SelectValue placeholder="选择题材母类" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">未设置</SelectItem>
                  <SelectItem value="xianxia">xianxia</SelectItem>
                  <SelectItem value="urban">urban</SelectItem>
                  <SelectItem value="historical_power">historical_power</SelectItem>
                  <SelectItem value="infinite_flow">infinite_flow</SelectItem>
                  <SelectItem value="gaming">gaming</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="generation-overlays">Overlay（逗号分隔）</Label>
              <Input id="generation-overlays" {...form.register("generation_desire_overlays")} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="generation-intensity">强度档位</Label>
              <Select
                value={selectedIntensityLevel ?? "__none__"}
                onValueChange={(val) => form.setValue("generation_intensity_level", val === "__none__" ? null : val)}
              >
                <SelectTrigger id="generation-intensity" aria-label="强度档位">
                  <SelectValue placeholder="选择强度档位" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">未设置</SelectItem>
                  <SelectItem value="plot_only">plot_only</SelectItem>
                  <SelectItem value="edge">edge</SelectItem>
                  <SelectItem value="explicit">explicit</SelectItem>
                  <SelectItem value="graphic">graphic</SelectItem>
                  <SelectItem value="fetish_extreme">fetish_extreme</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-status">状态</Label>
            <Select
              value={selectedStatus}
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
                    {selectedProviderId
                      ? selectedProvider
                        ? `${selectedProvider.label} / ${selectedProvider.default_model}`
                        : "选择 Provider"
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
                      {enabledProviders.map((provider) => (
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
                              selectedProviderId === provider.id ? "opacity-100" : "opacity-0"
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
              value={selectedStyleProfileId ?? "__none__"}
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
          <div className="grid gap-2">
            <Label htmlFor="project-plot-profile">情节档案</Label>
            <Select
              value={selectedPlotProfileId ?? "__none__"}
              onValueChange={(val) => form.setValue("plot_profile_id", val === "__none__" ? null : val)}
            >
              <SelectTrigger id="project-plot-profile" aria-label="情节档案" className="bg-background">
                <SelectValue placeholder="选择情节档案" />
              </SelectTrigger>
              <SelectContent className="border shadow-md rounded-md bg-popover text-popover-foreground">
                <SelectItem value="__none__" className="cursor-pointer">未挂载</SelectItem>
                {plotProfiles.map((profile) => (
                  <SelectItem key={profile.id} value={profile.id} className="cursor-pointer">
                    {profile.plot_name}
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

type ProjectPageMode = "new" | "detail";

export function ProjectPageClient({
  mode,
  projectId,
  initialProject,
  initialProviders,
  initialStyleProfiles,
  initialPlotProfiles,
}: {
  mode: ProjectPageMode;
  projectId?: string;
  initialProject?: Project;
  initialProviders: ProviderConfig[];
  initialStyleProfiles: StyleProfileListItem[];
  initialPlotProfiles: PlotProfileListItem[];
}) {
  const router = useRouter();
  const isDetailMode = mode === "detail";
  
  const mutation = useMutation({
    mutationFn: (payload: ProjectPayload | Partial<ProjectPayload>) => {
      if (isDetailMode && projectId) {
        return updateProjectAction(projectId, payload as Partial<ProjectPayload>);
      }
      return createProjectAction(payload as ProjectPayload);
    },
    onError: (error) => toast.error(error.message),
    onSuccess: async (project) => {
      if (isDetailMode) {
        toast.success("项目配置已保存");
        return;
      }
      toast.success("项目创建成功");
      router.replace(`/projects/${project.id}`);
    },
  });

  const breadcrumbName = isDetailMode ? initialProject?.name : "新建项目";
  const pageTitle = isDetailMode ? initialProject?.name : "新建项目";
  const pageDescription = isDetailMode
    ? "更新项目基本信息、默认模型与未来的 Style Profile 挂载入口。"
    : "先定义项目本身，再在下一阶段接入 Style Profile 和编辑器。";

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center text-sm text-muted-foreground">
        <Link href="/projects" className="hover:text-foreground transition-colors">
          项目管理
        </Link>
        <ChevronRight className="h-4 w-4 mx-1" />
        <span className="text-foreground font-medium">{breadcrumbName}</span>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{pageTitle}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {pageDescription}
          </p>
        </div>
      </div>

      <ProjectForm
        project={initialProject}
        providers={initialProviders}
        styleProfiles={initialStyleProfiles}
        plotProfiles={initialPlotProfiles}
        submitting={mutation.isPending}
        onSubmit={async (values) => {
          await mutation.mutateAsync(values as ProjectPayload | Partial<ProjectPayload>);
        }}
      />
    </div>
  );
}
