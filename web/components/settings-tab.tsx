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
import type { PlotProfileListItem, Project, ProviderConfig, StyleProfileListItem } from "@/lib/types";

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
    saveMutation.mutate({
      name,
      description,
      status,
      default_provider_id: providerId,
      default_model: model,
      style_profile_id: styleProfileId,
      plot_profile_id: plotProfileId,
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
