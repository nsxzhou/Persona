"use client";

import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Save, Wand2, Bot, BookTemplate } from "lucide-react";
import { toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";

import { updateProjectAction } from "@/app/(workspace)/projects/actions";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  GenerationProfile,
  PlotProfileListItem,
  Project,
  ProviderConfig,
  StyleProfileListItem,
} from "@/lib/types";

interface SettingsTabProps {
  project: Project;
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  plotProfiles: PlotProfileListItem[];
  onNameChange?: (name: string) => void;
}

type TabType = "generation" | "provider" | "profiles";

const OVERLAYS = [
  { id: "harem_collect", label: "后宫收集" },
  { id: "wife_steal", label: "夺妻" },
  { id: "reverse_ntr", label: "反 NTR" },
  { id: "hypnosis_control", label: "催眠控制" },
  { id: "corruption_fall", label: "堕落沉沦" },
  { id: "dominance_capture", label: "支配捕获" },
] as const;

export function SettingsTab({
  project,
  providers,
  styleProfiles,
  plotProfiles,
  onNameChange,
}: SettingsTabProps) {
  const [activeSidebarTab, setActiveSidebarTab] = useState<TabType>("generation");

  const [providerId, setProviderId] = useState(project.provider.id);
  const [model, setModel] = useState(project.default_model);
  const [styleProfileId, setStyleProfileId] = useState<string | null>(
    project.style_profile_id,
  );
  const [plotProfileId, setPlotProfileId] = useState<string | null>(
    project.plot_profile_id,
  );
  const [generationGenreMother, setGenerationGenreMother] = useState<GenerationProfile["genre_mother"] | null>(
    project.generation_profile?.genre_mother ?? null,
  );
  const [generationDesireOverlays, setGenerationDesireOverlays] = useState<string[]>(
    project.generation_profile?.desire_overlays ?? [],
  );
  const [generationIntensityLevel, setGenerationIntensityLevel] = useState<GenerationProfile["intensity_level"] | null>(
    project.generation_profile?.intensity_level ?? null,
  );
  const [generationPovMode, setGenerationPovMode] = useState<GenerationProfile["pov_mode"]>(
    project.generation_profile?.pov_mode ?? "limited_third",
  );
  const [generationMoralityAxis, setGenerationMoralityAxis] = useState<GenerationProfile["morality_axis"]>(
    project.generation_profile?.morality_axis ?? "gray_pragmatism",
  );
  const [generationPaceDensity, setGenerationPaceDensity] = useState<GenerationProfile["pace_density"]>(
    project.generation_profile?.pace_density ?? "balanced",
  );

  // Sync state when project changes (e.g. after successful save and revalidatePath)
  useEffect(() => {
    setProviderId(project.provider.id);
    setModel(project.default_model);
    setStyleProfileId(project.style_profile_id);
    setPlotProfileId(project.plot_profile_id);
    setGenerationGenreMother(project.generation_profile?.genre_mother ?? null);
    setGenerationDesireOverlays(project.generation_profile?.desire_overlays ?? []);
    setGenerationIntensityLevel(project.generation_profile?.intensity_level ?? null);
    setGenerationPovMode(project.generation_profile?.pov_mode ?? "limited_third");
    setGenerationMoralityAxis(project.generation_profile?.morality_axis ?? "gray_pragmatism");
    setGenerationPaceDensity(project.generation_profile?.pace_density ?? "balanced");
  }, [project]);

  const handleReset = () => {
    setProviderId(project.provider.id);
    setModel(project.default_model);
    setStyleProfileId(project.style_profile_id);
    setPlotProfileId(project.plot_profile_id);
    setGenerationGenreMother(project.generation_profile?.genre_mother ?? null);
    setGenerationDesireOverlays(project.generation_profile?.desire_overlays ?? []);
    setGenerationIntensityLevel(project.generation_profile?.intensity_level ?? null);
    setGenerationPovMode(project.generation_profile?.pov_mode ?? "limited_third");
    setGenerationMoralityAxis(project.generation_profile?.morality_axis ?? "gray_pragmatism");
    setGenerationPaceDensity(project.generation_profile?.pace_density ?? "balanced");
  };

  const isDirty =
    providerId !== project.provider.id ||
    model !== project.default_model ||
    styleProfileId !== project.style_profile_id ||
    plotProfileId !== project.plot_profile_id ||
    generationGenreMother !== (project.generation_profile?.genre_mother ?? null) ||
    JSON.stringify(generationDesireOverlays) !== JSON.stringify(project.generation_profile?.desire_overlays ?? []) ||
    generationIntensityLevel !== (project.generation_profile?.intensity_level ?? null) ||
    generationPovMode !== (project.generation_profile?.pov_mode ?? "limited_third") ||
    generationMoralityAxis !== (project.generation_profile?.morality_axis ?? "gray_pragmatism") ||
    generationPaceDensity !== (project.generation_profile?.pace_density ?? "balanced");

  const saveMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      updateProjectAction(
        project.id,
        payload as Partial<Record<string, string>>,
      ),
    onError: (error) => toast.error(error.message),
    onSuccess: () => toast.success("项目设置已保存"),
  });

  const handleSave = () => {
    const overlays = generationDesireOverlays as GenerationProfile["desire_overlays"];

    saveMutation.mutate({
      default_provider_id: providerId,
      default_model: model,
      style_profile_id: styleProfileId,
      plot_profile_id: plotProfileId,
      generation_profile:
        generationGenreMother && generationIntensityLevel
          ? {
            genre_mother: generationGenreMother,
            desire_overlays: overlays,
            intensity_level: generationIntensityLevel,
            pov_mode: generationPovMode,
            morality_axis: generationMoralityAxis,
            pace_density: generationPaceDensity,
          }
          : null,
    });
  };

  return (
    <div className="max-w-5xl mx-auto flex flex-col md:flex-row gap-8 pb-24">
      {/* Sidebar Navigation */}
      <aside className="md:w-64 shrink-0 space-y-1">
        <nav className="flex flex-col gap-1">
          <Button
            variant="ghost"
            className={cn(
              "justify-start",
              activeSidebarTab === "generation" && "bg-muted font-medium"
            )}
            onClick={() => setActiveSidebarTab("generation")}
          >
            <Wand2 className="mr-2 h-4 w-4" />
            生成策略
          </Button>
          <Button
            variant="ghost"
            className={cn(
              "justify-start",
              activeSidebarTab === "provider" && "bg-muted font-medium"
            )}
            onClick={() => setActiveSidebarTab("provider")}
          >
            <Bot className="mr-2 h-4 w-4" />
            AI 引擎配置
          </Button>
          <Button
            variant="ghost"
            className={cn(
              "justify-start",
              activeSidebarTab === "profiles" && "bg-muted font-medium"
            )}
            onClick={() => setActiveSidebarTab("profiles")}
          >
            <BookTemplate className="mr-2 h-4 w-4" />
            档案挂载
          </Button>
        </nav>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 space-y-6">
        {activeSidebarTab === "generation" && (
          <Card>
            <CardHeader>
              <CardTitle>生成策略 (Generation Profile)</CardTitle>
              <CardDescription>配置 AI 生成内容的风格、节奏和偏好。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-2">
                <Label htmlFor="settings-generation-genre">题材母类</Label>
                <Select
                  value={generationGenreMother ?? "__none__"}
                  onValueChange={(val) =>
                    setGenerationGenreMother(
                      val === "__none__" ? null : (val as GenerationProfile["genre_mother"]),
                    )
                  }
                >
                  <SelectTrigger id="settings-generation-genre" aria-label="题材母类" className="bg-background">
                    <SelectValue placeholder="选择题材母类" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">未设置</SelectItem>
                    <SelectItem value="xianxia">仙侠（xianxia）</SelectItem>
                    <SelectItem value="urban">都市（urban）</SelectItem>
                    <SelectItem value="historical_power">历史权谋（historical_power）</SelectItem>
                    <SelectItem value="infinite_flow">无限流（infinite_flow）</SelectItem>
                    <SelectItem value="gaming">游戏竞技（gaming）</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>Overlay（多选）</Label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
                  {OVERLAYS.map((overlay) => (
                    <div key={overlay.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={`overlay-${overlay.id}`}
                        checked={generationDesireOverlays.includes(overlay.id)}
                        onCheckedChange={(checked) => {
                          setGenerationDesireOverlays((prev) =>
                            checked
                              ? [...prev, overlay.id]
                              : prev.filter((id) => id !== overlay.id)
                          );
                        }}
                      />
                      <label
                        htmlFor={`overlay-${overlay.id}`}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                      >
                        {overlay.label}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="settings-generation-intensity">强度档位</Label>
                <Select
                  value={generationIntensityLevel ?? "__none__"}
                  onValueChange={(val) =>
                    setGenerationIntensityLevel(
                      val === "__none__" ? null : (val as GenerationProfile["intensity_level"]),
                    )
                  }
                >
                  <SelectTrigger id="settings-generation-intensity" aria-label="强度档位" className="bg-background">
                    <SelectValue placeholder="选择强度档位" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">未设置</SelectItem>
                    <SelectItem value="plot_only">剧情优先（plot_only）</SelectItem>
                    <SelectItem value="edge">边缘暧昧（edge）</SelectItem>
                    <SelectItem value="explicit">露骨描写（explicit）</SelectItem>
                    <SelectItem value="graphic">强烈直白（graphic）</SelectItem>
                    <SelectItem value="fetish_extreme">极端癖好（fetish_extreme）</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="settings-generation-pov">叙事视角</Label>
                <Select
                  value={generationPovMode}
                  onValueChange={(val) => setGenerationPovMode(val as GenerationProfile["pov_mode"])}
                >
                  <SelectTrigger id="settings-generation-pov" aria-label="叙事视角" className="bg-background">
                    <SelectValue placeholder="选择叙事视角" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="limited_third">限制性第三人称（limited_third）</SelectItem>
                    <SelectItem value="first_person">第一人称（first_person）</SelectItem>
                    <SelectItem value="deep_first">深度第一人称（deep_first）</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="settings-generation-morality">道德轴</Label>
                <Select
                  value={generationMoralityAxis}
                  onValueChange={(val) => setGenerationMoralityAxis(val as GenerationProfile["morality_axis"])}
                >
                  <SelectTrigger id="settings-generation-morality" aria-label="道德轴" className="bg-background">
                    <SelectValue placeholder="选择道德轴" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ruthless_growth">冷酷成长（ruthless_growth）</SelectItem>
                    <SelectItem value="gray_pragmatism">灰度务实（gray_pragmatism）</SelectItem>
                    <SelectItem value="domination_first">支配优先（domination_first）</SelectItem>
                    <SelectItem value="vengeful">复仇驱动（vengeful）</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="settings-generation-pace">节奏密度</Label>
                <Select
                  value={generationPaceDensity}
                  onValueChange={(val) => setGenerationPaceDensity(val as GenerationProfile["pace_density"])}
                >
                  <SelectTrigger id="settings-generation-pace" aria-label="节奏密度" className="bg-background">
                    <SelectValue placeholder="选择节奏密度" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="slow">慢节奏（slow）</SelectItem>
                    <SelectItem value="balanced">均衡（balanced）</SelectItem>
                    <SelectItem value="fast">快节奏（fast）</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        )}

        {activeSidebarTab === "provider" && (
          <Card>
            <CardHeader>
              <CardTitle>AI 引擎配置</CardTitle>
              <CardDescription>配置项目默认使用的 AI Provider 和模型。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-2">
                <Label>默认 Provider</Label>
                <Select value={providerId} onValueChange={setProviderId}>
                  <SelectTrigger className="bg-background">
                    <SelectValue placeholder="选择 Provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {providers
                      .filter((p) => p.is_enabled || p.id === project.provider.id)
                      .map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.label} / {p.default_model}
                          {!p.is_enabled && " (已禁用)"}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="settings-model">项目默认模型</Label>
                <Input
                  id="settings-model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="留空则回退到 Provider 默认模型"
                />
              </div>
            </CardContent>
          </Card>
        )}

        {activeSidebarTab === "profiles" && (
          <Card>
            <CardHeader>
              <CardTitle>档案挂载</CardTitle>
              <CardDescription>选择项目应用的风格档案和情节档案。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-2">
                <Label>风格档案</Label>
                <Select
                  value={styleProfileId ?? "__none__"}
                  onValueChange={(val) =>
                    setStyleProfileId(val === "__none__" ? null : val)
                  }
                >
                  <SelectTrigger className="bg-background">
                    <SelectValue placeholder="选择风格档案" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">未挂载</SelectItem>
                    {styleProfiles.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.style_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label>情节档案</Label>
                <Select
                  value={plotProfileId ?? "__none__"}
                  onValueChange={(val) =>
                    setPlotProfileId(val === "__none__" ? null : val)
                  }
                >
                  <SelectTrigger className="bg-background">
                    <SelectValue placeholder="选择情节档案" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">未挂载</SelectItem>
                    {plotProfiles.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.plot_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Floating Action Bar */}
      <AnimatePresence>
        {isDirty && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 rounded-full border bg-background px-6 py-3 shadow-lg"
          >
            <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
              您有未保存的更改
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleReset}
                disabled={saveMutation.isPending}
                className="rounded-full"
              >
                取消
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={saveMutation.isPending}
                className="rounded-full gap-2"
              >
                <Save className="h-4 w-4" />
                保存更改
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
