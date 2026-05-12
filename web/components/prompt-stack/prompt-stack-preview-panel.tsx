import { Eye, FileText, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  layerTitleLabel,
  reasonLabel,
} from "@/lib/prompt-stack-labels";
import type { ProjectChapter, PromptStackPreviewResponse } from "@/lib/types";

import {
  PromptStackCollapsiblePanel,
  PromptStackEmptyPanel,
  PromptStackField,
} from "./prompt-stack-panel";
import { formatPromptStackChars } from "./prompt-stack-utils";
import type {
  PromptStackLayerManifestItem,
  PromptStackPreviewContext,
} from "./types";

const ALL_CHAPTERS_PREVIEW_VALUE = "__all_chapters__";

export function PromptStackPreviewPanel({
  open,
  onOpenChange,
  preview,
  previewContext,
  chapters,
  assetCount,
  isPreviewing,
  onPreviewContextChange,
  onPreview,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  preview: PromptStackPreviewResponse | null;
  previewContext: PromptStackPreviewContext;
  chapters: ProjectChapter[];
  assetCount: number;
  isPreviewing: boolean;
  onPreviewContextChange: (
    next:
      | PromptStackPreviewContext
      | ((prev: PromptStackPreviewContext) => PromptStackPreviewContext),
  ) => void;
  onPreview: () => void;
}) {
  return (
    <PromptStackCollapsiblePanel
      title="运行时预览诊断"
      description="检查当前上下文会命中哪些 Prompt 栈资产。"
      icon={<Eye className="h-5 w-5 text-primary" />}
      open={open}
      onOpenChange={onOpenChange}
      rightSlot={
        <Badge variant={preview ? "secondary" : "outline"}>
          {preview ? `${preview.manifest.total_selected_assets} 项命中` : "未运行"}
        </Badge>
      }
    >
      <div className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4">
          <PromptStackField label="预览章节">
            <Select
              value={previewContext.chapter_id || ALL_CHAPTERS_PREVIEW_VALUE}
              onValueChange={(value) =>
                onPreviewContextChange((prev) => ({
                  ...prev,
                  chapter_id: value === ALL_CHAPTERS_PREVIEW_VALUE ? "" : value,
                }))
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="不限定章节" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_CHAPTERS_PREVIEW_VALUE}>不限定章节</SelectItem>
                {chapters.map((chapter) => (
                  <SelectItem key={chapter.id} value={chapter.id}>
                    {chapter.title || `第 ${chapter.chapter_index + 1} 章`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </PromptStackField>
          <PromptStackField label="当前章节上下文">
            <Textarea
              className="min-h-24"
              value={previewContext.current_chapter_context}
              onChange={(event) =>
                onPreviewContextChange((prev) => ({
                  ...prev,
                  current_chapter_context: event.target.value,
                }))
              }
            />
          </PromptStackField>
          <PromptStackField label="光标前正文">
            <Textarea
              className="min-h-24"
              value={previewContext.text_before_cursor}
              onChange={(event) =>
                onPreviewContextChange((prev) => ({
                  ...prev,
                  text_before_cursor: event.target.value,
                }))
              }
            />
          </PromptStackField>
          <PromptStackField label="用户上下文">
            <Textarea
              className="min-h-20"
              value={previewContext.user_context}
              onChange={(event) =>
                onPreviewContextChange((prev) => ({
                  ...prev,
                  user_context: event.target.value,
                }))
              }
            />
          </PromptStackField>
          <Button type="button" className="w-full" onClick={onPreview} disabled={isPreviewing}>
            <Eye className="mr-1.5 h-4 w-4" />
            {isPreviewing ? "预览中..." : "预览注入结果"}
          </Button>
        </div>

        <PromptStackDiagnostics preview={preview} assetCount={assetCount} />
      </div>
    </PromptStackCollapsiblePanel>
  );
}

function PromptStackDiagnostics({
  preview,
  assetCount,
}: {
  preview: PromptStackPreviewResponse | null;
  assetCount: number;
}) {
  if (!preview) {
    return (
      <PromptStackEmptyPanel
        icon={<Search className="h-5 w-5" />}
        title="等待预览"
        description={
          assetCount > 0
            ? "填写上下文后预览，资产命中、层级和最终 Prompt 会显示在这里。"
            : "当前没有 Prompt 栈资产可命中；基础小说资产仍会在生成时照常注入。"
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        {preview.manifest.layers.length > 0 ? (
          preview.manifest.layers.map((layer) => (
            <LayerDiagnostics key={layer.key} layer={layer} />
          ))
        ) : (
          <PromptStackEmptyPanel
            title="本次没有 Prompt 栈资产进入 Prompt"
            description="当前上下文未命中关键词，也没有匹配作用域的 Always-on 资产。基础小说资产仍会注入。"
          />
        )}
      </div>
      <div className="rounded-lg border-2">
        <div className="flex items-center justify-between border-b-2 px-3 py-2">
          <div className="flex items-center gap-2 text-sm font-medium">
            <FileText className="h-4 w-4" />
            最终 Prompt 栈片段
          </div>
          <span className="text-xs text-muted-foreground">
            {formatPromptStackChars(preview.manifest.final_prompt_char_count)}
          </span>
        </div>
        <pre className="max-h-[360px] overflow-auto p-3 text-xs whitespace-pre-wrap">
          {preview.prompt || "未选中任何 Prompt 栈资产。"}
        </pre>
      </div>
    </div>
  );
}

function LayerDiagnostics({ layer }: { layer: PromptStackLayerManifestItem }) {
  const assets = layer.assets ?? [];
  return (
    <div className="rounded-lg border-2 bg-background p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="font-medium">{layerTitleLabel(layer.title)}</div>
          <div className="mt-1 text-xs text-muted-foreground">
            {assets.length} 项资产 · {formatPromptStackChars(layer.char_count)}
          </div>
        </div>
        <Badge variant="outline">{layer.key}</Badge>
      </div>
      <div className="mt-3 grid gap-2">
        {assets.map((asset) => (
          <div key={asset.id} className="rounded-md bg-muted/30 p-2 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium">{asset.title}</span>
              <span className="text-xs text-muted-foreground">P{asset.priority}</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {asset.match_reasons.map((reason) => (
                <Badge key={reason} variant="secondary">
                  {reasonLabel(reason)}
                </Badge>
              ))}
              {asset.matched_keywords.map((keyword) => (
                <Badge key={keyword} variant="outline">
                  #{keyword}
                </Badge>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
