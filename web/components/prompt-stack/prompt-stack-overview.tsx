import { Layers3, Pencil, Plus, Sparkles, WandSparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { kindLabel, reasonLabel, scopeLabel } from "@/lib/prompt-stack-labels";
import { cn } from "@/lib/utils";
import type { ProjectPromptAsset } from "@/lib/types";

import type { PromptStackAssetManifestItem } from "./types";

export function PromptStackSummary({
  assetCount,
  enabledCount,
  alwaysOnCount,
  keywordTriggeredCount,
}: {
  assetCount: number;
  enabledCount: number;
  alwaysOnCount: number;
  keywordTriggeredCount: number;
}) {
  return (
    <section className="rounded-lg border-2 bg-card p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <div className="flex items-center gap-2">
            <Layers3 className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Prompt 栈资产</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Prompt 栈是可选增强层。即使这里为空，项目简介、世界观、角色关系、细纲、运行时状态等基础小说资产仍会进入生成上下文；这里用于补充可按章节、关键词或 Always-on 规则动态注入的细粒度资料。
          </p>
        </div>
        <div className="grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[520px]">
          <Metric label="资产" value={String(assetCount)} detail="总数" />
          <Metric label="启用" value={String(enabledCount)} detail="可参与注入" />
          <Metric label="Always-on" value={String(alwaysOnCount)} detail="作用域匹配即注入" />
          <Metric label="关键词" value={String(keywordTriggeredCount)} detail="命中上下文注入" />
        </div>
      </div>
    </section>
  );
}

export function EmptyPromptStackState({
  isGeneratingSuggestions,
  onGenerateSuggestions,
  onCreateAsset,
}: {
  isGeneratingSuggestions: boolean;
  onGenerateSuggestions: () => void;
  onCreateAsset: () => void;
}) {
  return (
    <section className="rounded-lg border-2 border-dashed bg-background p-6">
      <div className="mx-auto max-w-2xl text-center">
        <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full border-2 bg-card">
          <WandSparkles className="h-5 w-5 text-primary" />
        </div>
        <h3 className="mt-4 text-lg font-semibold">还没有 Prompt 栈资产</h3>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          这不会阻止小说生成。基础小说资产会照常注入；你可以在需要更精细控制某些设定、角色卡或作者注释时，再创建 Prompt 栈资产。
        </p>
        <div className="mt-5 flex flex-col justify-center gap-3 sm:flex-row">
          <Button type="button" onClick={onGenerateSuggestions} disabled={isGeneratingSuggestions}>
            <Sparkles className="mr-1.5 h-4 w-4" />
            {isGeneratingSuggestions ? "生成中..." : "生成初始化建议"}
          </Button>
          <Button type="button" variant="outline" onClick={onCreateAsset}>
            <Plus className="mr-1.5 h-4 w-4" />
            手动新建资产
          </Button>
        </div>
      </div>
    </section>
  );
}

export function PromptAssetTable({
  assets,
  isLoading,
  selectedId,
  selectedManifestById,
  hasPreview,
  onCreateAsset,
  onEditAsset,
}: {
  assets: ProjectPromptAsset[];
  isLoading: boolean;
  selectedId: string | null;
  selectedManifestById: Map<string, PromptStackAssetManifestItem>;
  hasPreview: boolean;
  onCreateAsset: () => void;
  onEditAsset: (assetId: string) => void;
}) {
  return (
    <section className="overflow-hidden rounded-lg border-2 bg-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 p-4">
        <div>
          <h3 className="text-base font-semibold">资产管理</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            扫描资产类型、触发方式、作用域和优先级。
          </p>
        </div>
        <Button type="button" onClick={onCreateAsset}>
          <Plus className="mr-1.5 h-4 w-4" />
          新建资产
        </Button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] border-collapse text-sm">
          <thead className="bg-muted/40 text-left text-xs font-medium text-muted-foreground">
            <tr>
              <th className="px-4 py-3">资产</th>
              <th className="px-4 py-3">类型</th>
              <th className="px-4 py-3">作用域</th>
              <th className="px-4 py-3">触发方式</th>
              <th className="px-4 py-3">优先级</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td className="px-4 py-8 text-center text-muted-foreground" colSpan={7}>
                  正在加载...
                </td>
              </tr>
            ) : null}
            {assets.map((asset) => {
              const manifest = selectedManifestById.get(asset.id);
              return (
                <tr
                  key={asset.id}
                  className={cn(
                    "border-t-2 transition-colors",
                    selectedId === asset.id ? "bg-primary/5" : "hover:bg-muted/30",
                  )}
                >
                  <td className="px-4 py-3 align-top">
                    <div className="font-medium leading-5">{asset.title}</div>
                    <div className="mt-1 line-clamp-2 max-w-[320px] text-xs leading-5 text-muted-foreground">
                      {asset.content || "未填写内容"}
                    </div>
                  </td>
                  <td className="px-4 py-3 align-top">
                    <Badge variant="outline">{kindLabel(asset.kind)}</Badge>
                  </td>
                  <td className="px-4 py-3 align-top">{scopeLabel(asset.scope)}</td>
                  <td className="px-4 py-3 align-top">
                    <TriggerSummary asset={asset} />
                  </td>
                  <td className="px-4 py-3 align-top tabular-nums">P{asset.priority}</td>
                  <td className="px-4 py-3 align-top">
                    <div className="flex flex-wrap gap-1.5">
                      <AssetRuntimeBadge asset={asset} manifest={manifest} hasPreview={hasPreview} />
                      {manifest?.match_reasons.map((reason) => (
                        <Badge key={reason} variant="secondary">
                          {reasonLabel(reason)}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right align-top">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => onEditAsset(asset.id)}
                    >
                      <Pencil className="mr-1.5 h-4 w-4" />
                      编辑
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TriggerSummary({ asset }: { asset: ProjectPromptAsset }) {
  if (!asset.enabled) {
    return <span className="text-muted-foreground">禁用</span>;
  }
  const triggerParts = [];
  if (asset.always_on) triggerParts.push("Always-on");
  if (asset.keywords.length > 0) triggerParts.push(`${asset.keywords.length} 个关键词`);
  if (triggerParts.length === 0) {
    return <span className="text-muted-foreground">未设置触发</span>;
  }
  return (
    <div className="space-y-1">
      <div>{triggerParts.join(" / ")}</div>
      {asset.keywords.length > 0 ? (
        <div className="flex max-w-[240px] flex-wrap gap-1">
          {asset.keywords.slice(0, 4).map((keyword) => (
            <span key={keyword} className="text-xs text-muted-foreground">
              #{keyword}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function AssetRuntimeBadge({
  asset,
  manifest,
  hasPreview,
}: {
  asset: ProjectPromptAsset;
  manifest: PromptStackAssetManifestItem | undefined;
  hasPreview: boolean;
}) {
  if (!asset.enabled) return <Badge variant="outline">禁用</Badge>;
  if (!hasPreview) return <Badge variant="secondary">启用</Badge>;
  if (manifest) return <Badge>本次命中</Badge>;
  return <Badge variant="outline">未命中</Badge>;
}

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-md border-2 bg-background p-3">
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold leading-none">{value}</div>
      <div className="mt-2 text-xs text-muted-foreground">{detail}</div>
    </div>
  );
}
