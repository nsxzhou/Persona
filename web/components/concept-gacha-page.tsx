"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, RefreshCw, Sparkles } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

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
import { api } from "@/lib/api";
import { createProjectAction } from "@/app/(workspace)/projects/actions";
import { LENGTH_PRESETS, type LengthPresetKey } from "@/lib/length-presets";
import type { ConceptItem, ProviderConfig } from "@/lib/types";

interface ConceptGachaPageProps {
  providers: ProviderConfig[];
}

export function ConceptGachaPage({ providers }: ConceptGachaPageProps) {
  const router = useRouter();
  const enabledProviders = providers.filter((p) => p.is_enabled);

  const [providerId, setProviderId] = useState(enabledProviders[0]?.id ?? "");
  const [model, setModel] = useState("");
  const [inspiration, setInspiration] = useState("");
  const [concepts, setConcepts] = useState<ConceptItem[] | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lengthPreset, setLengthPreset] = useState<LengthPresetKey>("short");

  const handleGenerate = async () => {
    if (!providerId || !inspiration.trim()) return;
    setIsGenerating(true);
    setError(null);
    setConcepts(null);
    setSelectedIndex(null);

    try {
      const result = await api.generateConcepts({
        inspiration: inspiration.trim(),
        provider_id: providerId,
        model: model.trim() || null,
        count: 3,
      });
      setConcepts(result.concepts);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "生成失败，请重试";
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleConfirm = async () => {
    if (selectedIndex === null || !concepts) return;
    const selected = concepts[selectedIndex];

    setIsCreating(true);
    try {
      const project = await createProjectAction({
        name: selected.title,
        description: selected.synopsis,
        inspiration: inspiration.trim(),
        default_provider_id: providerId,
        default_model: model.trim() || null,
        status: "draft",
        world_building: "",
        characters: "",
        outline_master: "",
        outline_detail: "",
        story_bible: "",
        content: "",
        length_preset: lengthPreset,
      });
      router.replace(`/projects/${project.id}`);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "创建失败";
      toast.error(message);
      setIsCreating(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/projects" className="text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <h1 className="text-lg font-semibold">新建小说</h1>
      </div>

      {/* Provider + Model */}
      <div className="grid grid-cols-2 gap-4">
        <div className="grid gap-2">
          <Label>AI 服务商</Label>
          <Select value={providerId} onValueChange={setProviderId}>
            <SelectTrigger className="bg-background">
              <SelectValue placeholder="选择 Provider" />
            </SelectTrigger>
            <SelectContent>
              {enabledProviders.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.label} · {p.default_model}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="gacha-model">模型（可选）</Label>
          <Input
            id="gacha-model"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="留空使用默认"
          />
        </div>
      </div>

      {/* Inspiration input */}
      <div className="grid gap-2">
        <Label htmlFor="gacha-inspiration">你的灵感</Label>
        <textarea
          id="gacha-inspiration"
          value={inspiration}
          onChange={(e) => setInspiration(e.target.value)}
          placeholder='在这里描述你的小说灵感、主题、世界观雏形、想要的故事走向...&#10;&#10;例："一个失忆的少年在末世废墟中醒来，发现自己手臂上刻着倒计时..."'
          className="w-full min-h-[120px] resize-y rounded-md border border-input bg-background px-3 py-2 text-sm leading-relaxed placeholder:text-muted-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <div className="flex justify-end">
          <Button
            onClick={handleGenerate}
            disabled={isGenerating || !providerId || !inspiration.trim()}
            className="gap-2"
          >
            {isGenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isGenerating ? "生成中..." : "生成灵感卡"}
          </Button>
        </div>
      </div>

      {/* Divider */}
      <hr className="border-border" />

      {/* Cards area */}
      {isGenerating && !concepts && (
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="animate-pulse rounded-xl border border-border p-5 space-y-3"
            >
              <div className="h-5 w-2/3 rounded bg-muted" />
              <div className="space-y-2">
                <div className="h-3 w-full rounded bg-muted" />
                <div className="h-3 w-4/5 rounded bg-muted" />
              </div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="flex flex-col items-center gap-3 py-8">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={handleGenerate}>
            重试
          </Button>
        </div>
      )}

      {concepts && (
        <>
          <div className="grid grid-cols-3 gap-4">
            {concepts.map((concept, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setSelectedIndex(i)}
                className={`relative rounded-xl border-2 p-5 text-left transition-all ${
                  selectedIndex === i
                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                    : "border-border hover:border-muted-foreground/30"
                }`}
              >
                {selectedIndex === i && (
                  <span className="absolute -top-2 left-3 rounded bg-primary px-2 py-0.5 text-[10px] font-medium text-primary-foreground">
                    选中
                  </span>
                )}
                <h3 className="font-medium text-sm mb-2">{concept.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {concept.synopsis}
                </p>
              </button>
            ))}
          </div>

          {/* Length Preset Selector */}
          {selectedIndex !== null && (
            <div className="space-y-3">
              <Label>篇幅范围</Label>
              <div className="grid grid-cols-3 gap-3">
                {(Object.entries(LENGTH_PRESETS) as [LengthPresetKey, (typeof LENGTH_PRESETS)[LengthPresetKey]][]).map(
                  ([key, cfg]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setLengthPreset(key)}
                      className={`rounded-lg border-2 p-4 text-left transition-all ${
                        lengthPreset === key
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-muted-foreground/30"
                      }`}
                    >
                      <div className="font-medium text-sm">{cfg.label}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {cfg.targetMin / 10000}-{cfg.targetMax / 10000} 万字
                      </div>
                      <div className="text-xs text-muted-foreground/70 mt-0.5">
                        {cfg.description}
                      </div>
                    </button>
                  ),
                )}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerate}
              disabled={isGenerating}
              className="gap-1.5"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isGenerating ? "animate-spin" : ""}`} />
              全部重新生成
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={selectedIndex === null || isCreating}
              className="gap-2"
            >
              {isCreating && <Loader2 className="h-4 w-4 animate-spin" />}
              确认选择
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
