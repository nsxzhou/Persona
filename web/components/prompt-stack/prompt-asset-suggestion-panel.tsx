import { Check, Sparkles, WandSparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  actionLabel,
  kindLabel,
} from "@/lib/prompt-stack-labels";
import type {
  PromptAssetInitSuggestionsResponse,
  ProjectPromptAsset,
  ProjectPromptAssetSuggestionChange,
} from "@/lib/types";

import {
  PromptStackCollapsiblePanel,
  PromptStackEmptyPanel,
} from "./prompt-stack-panel";

export function PromptAssetSuggestionPanel({
  open,
  onOpenChange,
  suggestions,
  assets,
  isGenerating,
  isApplying,
  onGenerate,
  onApply,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  suggestions: PromptAssetInitSuggestionsResponse | null;
  assets: ProjectPromptAsset[];
  isGenerating: boolean;
  isApplying: boolean;
  onGenerate: () => void;
  onApply: () => void;
}) {
  return (
    <PromptStackCollapsiblePanel
      title="初始化建议"
      description="根据项目资料生成新增、更新、禁用建议。"
      icon={<WandSparkles className="h-5 w-5 text-primary" />}
      open={open}
      onOpenChange={onOpenChange}
      rightSlot={
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={(event) => {
              event.stopPropagation();
              onGenerate();
            }}
            disabled={isGenerating}
          >
            <Sparkles className="mr-1.5 h-4 w-4" />
            {isGenerating ? "生成中..." : "生成"}
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={(event) => {
              event.stopPropagation();
              onApply();
            }}
            disabled={!suggestions?.changes.length || isApplying}
          >
            <Check className="mr-1.5 h-4 w-4" />
            写回
          </Button>
        </div>
      }
    >
      {suggestions ? (
        <PromptAssetSuggestions changes={suggestions.changes} assets={assets} />
      ) : (
        <PromptStackEmptyPanel
          title="尚未生成建议"
          description="点击生成后，建议会按新增、更新、禁用分组展示。"
        />
      )}
    </PromptStackCollapsiblePanel>
  );
}

function PromptAssetSuggestions({
  changes,
  assets,
}: {
  changes: ProjectPromptAssetSuggestionChange[];
  assets: ProjectPromptAsset[];
}) {
  const grouped = {
    new: changes.filter((change) => change.action === "new"),
    update: changes.filter((change) => change.action === "update"),
    disable: changes.filter((change) => change.action === "disable"),
  };
  return (
    <div className="grid gap-3">
      {(["new", "update", "disable"] as const).map((action) => {
        const actionChanges = grouped[action];
        if (actionChanges.length === 0) return null;
        return (
          <div key={action} className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">{actionLabel(action)}</Badge>
              <span className="text-xs text-muted-foreground">{actionChanges.length} 项</span>
            </div>
            <div className="grid gap-2">
              {actionChanges.map((change, index) => {
                const existing = assets.find((asset) => asset.id === change.asset_id);
                const payload = change.payload;
                return (
                  <div key={`${action}-${change.asset_id ?? index}`} className="rounded-md border-2 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{payload?.title || existing?.title || change.asset_id}</span>
                      {payload?.kind ? <Badge variant="outline">{kindLabel(payload.kind)}</Badge> : null}
                    </div>
                    {change.rationale ? (
                      <p className="mt-2 text-xs text-muted-foreground">{change.rationale}</p>
                    ) : null}
                    {payload ? (
                      <div className="mt-2 grid gap-2">
                        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                          <span>P{payload.priority}</span>
                          {payload.always_on ? <span>Always-on</span> : null}
                          {(payload.keywords ?? []).map((keyword) => (
                            <span key={keyword}>#{keyword}</span>
                          ))}
                        </div>
                        <pre className="max-h-40 overflow-auto rounded-md bg-muted/30 p-2 text-xs whitespace-pre-wrap">
                          {payload.content}
                        </pre>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
      {changes.length === 0 ? (
        <PromptStackEmptyPanel title="没有需要写回的建议" description="当前资产库不需要调整。" />
      ) : null}
    </div>
  );
}
