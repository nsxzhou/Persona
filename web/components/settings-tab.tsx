"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { toast } from "sonner";

import { updateProjectAction } from "@/app/(workspace)/projects/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
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

export function SettingsTab({
  project,
  providers,
  styleProfiles,
  plotProfiles,
  onNameChange,
}: SettingsTabProps) {
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description);
  const [status, setStatus] = useState(project.status);
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
  const [generationDesireOverlays, setGenerationDesireOverlays] = useState(
    project.generation_profile?.desire_overlays?.join(", ") ?? "",
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
    const overlays = generationDesireOverlays
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean) as GenerationProfile["desire_overlays"];

    saveMutation.mutate({
      name,
      description,
      status,
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

  const handleNameChange = (value: string) => {
    setName(value);
    onNameChange?.(value);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Project name */}
      <div className="grid gap-2">
        <Label htmlFor="settings-name">项目名称</Label>
        <Input
          id="settings-name"
          value={name}
          onChange={(e) => handleNameChange(e.target.value)}
        />
      </div>

      {/* Description */}
      <div className="grid gap-2">
        <Label htmlFor="settings-desc">简介</Label>
        <Textarea
          id="settings-desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="min-h-[100px] resize-y"
        />
      </div>

      {/* Status */}
      <div className="grid gap-2">
        <Label>状态</Label>
        <Select value={status} onValueChange={(val: "draft" | "active" | "paused") => setStatus(val)}>
          <SelectTrigger className="bg-background">
            <SelectValue placeholder="选择状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="draft">draft</SelectItem>
            <SelectItem value="active">active</SelectItem>
            <SelectItem value="paused">paused</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 rounded-lg border p-4">
        <div className="text-sm font-medium">生成策略（Generation Profile）</div>
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
          <Label htmlFor="settings-generation-overlays">Overlay（逗号分隔）</Label>
          <Input
            id="settings-generation-overlays"
            value={generationDesireOverlays}
            onChange={(e) => setGenerationDesireOverlays(e.target.value)}
            placeholder="例如：harem_collect, hypnosis_control"
          />
          <p className="text-xs text-muted-foreground">
            可选值：后宫收集（harem_collect）、夺妻（wife_steal）、反 NTR（reverse_ntr）、催眠控制（hypnosis_control）、堕落沉沦（corruption_fall）、支配捕获（dominance_capture）
          </p>
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
      </div>

      <hr className="border-border" />

      {/* Provider */}
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

      {/* Model */}
      <div className="grid gap-2">
        <Label htmlFor="settings-model">项目默认模型</Label>
        <Input
          id="settings-model"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="留空则回退到 Provider 默认模型"
        />
      </div>

      {/* Style profile */}
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

      <hr className="border-border" />

      {/* Save */}
      <div className="flex justify-end">
        <Button
          onClick={handleSave}
          disabled={saveMutation.isPending}
          className="gap-2"
        >
          <Save className="h-4 w-4" />
          保存配置
        </Button>
      </div>
    </div>
  );
}
