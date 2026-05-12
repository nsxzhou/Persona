import { Save, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  PROMPT_ASSET_KIND_OPTIONS as KIND_OPTIONS,
  PROMPT_ASSET_SCOPE_OPTIONS as SCOPE_OPTIONS,
  reasonLabel,
} from "@/lib/prompt-stack-labels";
import type {
  ProjectChapter,
  ProjectPromptAsset,
  ProjectPromptAssetCreate,
} from "@/lib/types";

import {
  PromptStackField,
  PromptStackSwitchField,
} from "./prompt-stack-panel";
import type {
  AssetKind,
  AssetScope,
  PromptStackAssetManifestItem,
} from "./types";

export function PromptAssetEditor({
  form,
  keywordText,
  selectedAsset,
  selectedManifest,
  chapters,
  onFormChange,
  onKeywordTextChange,
  onSave,
  onDelete,
  onCancel,
  isSaving,
  isDeleting,
}: {
  form: ProjectPromptAssetCreate;
  keywordText: string;
  selectedAsset: ProjectPromptAsset | null;
  selectedManifest: PromptStackAssetManifestItem | undefined;
  chapters: ProjectChapter[];
  onFormChange: (
    next: ProjectPromptAssetCreate | ((prev: ProjectPromptAssetCreate) => ProjectPromptAssetCreate),
  ) => void;
  onKeywordTextChange: (next: string) => void;
  onSave: () => void;
  onDelete: () => void;
  onCancel: () => void;
  isSaving: boolean;
  isDeleting: boolean;
}) {
  return (
    <section className="rounded-lg border-2 bg-card">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b-2 p-4">
        <div>
          <h3 className="text-base font-semibold">
            {selectedAsset ? "编辑资产" : "新建资产"}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            内容会作为参考资料进入 Prompt 栈，触发规则决定它何时生效。
          </p>
          {selectedManifest ? (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {selectedManifest.match_reasons.map((reason) => (
                <Badge key={reason}>{reasonLabel(reason)}</Badge>
              ))}
              {selectedManifest.matched_keywords.map((keyword) => (
                <Badge key={keyword} variant="outline">
                  #{keyword}
                </Badge>
              ))}
            </div>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" onClick={onSave} disabled={isSaving}>
            <Save className="mr-1.5 h-4 w-4" />
            保存
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={onDelete}
            disabled={!selectedAsset || isDeleting}
          >
            <Trash2 className="mr-1.5 h-4 w-4" />
            删除
          </Button>
          <Button type="button" variant="outline" onClick={onCancel}>
            收起
          </Button>
        </div>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-4">
        <PromptStackField label="类型">
          <Select
            value={form.kind}
            onValueChange={(value: AssetKind) =>
              onFormChange((prev) => ({ ...prev, kind: value }))
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {KIND_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </PromptStackField>
        <PromptStackField label="作用域">
          <Select
            value={form.scope}
            onValueChange={(value: AssetScope) =>
              onFormChange((prev) => ({
                ...prev,
                scope: value,
                chapter_id: value === "project" ? null : prev.chapter_id,
              }))
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SCOPE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </PromptStackField>
        {form.scope === "chapter" ? (
          <PromptStackField label="章节">
            <Select
              value={form.chapter_id ?? ""}
              onValueChange={(value) =>
                onFormChange((prev) => ({ ...prev, chapter_id: value }))
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="选择章节" />
              </SelectTrigger>
              <SelectContent>
                {chapters.map((chapter) => (
                  <SelectItem key={chapter.id} value={chapter.id}>
                    {chapter.title || `第 ${chapter.chapter_index + 1} 章`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </PromptStackField>
        ) : null}
        <PromptStackField label="优先级">
          <Input
            type="number"
            value={String(form.priority)}
            onChange={(event) =>
              onFormChange((prev) => ({ ...prev, priority: Number(event.target.value) || 0 }))
            }
          />
        </PromptStackField>
        <div className="lg:col-span-2">
          <PromptStackField label="标题">
            <Input
              value={form.title}
              onChange={(event) => onFormChange((prev) => ({ ...prev, title: event.target.value }))}
            />
          </PromptStackField>
        </div>
        <div className="lg:col-span-2">
          <PromptStackField label="关键词">
            <Input
              value={keywordText}
              onChange={(event) => onKeywordTextChange(event.target.value)}
              placeholder="逗号分隔"
            />
          </PromptStackField>
        </div>
        <div className="flex flex-wrap items-center gap-6 lg:col-span-4">
          <PromptStackSwitchField
            label="启用"
            checked={form.enabled}
            onCheckedChange={(checked) => onFormChange((prev) => ({ ...prev, enabled: checked }))}
          />
          <PromptStackSwitchField
            label="Always-on"
            checked={form.always_on}
            onCheckedChange={(checked) =>
              onFormChange((prev) => ({ ...prev, always_on: checked }))
            }
          />
        </div>
        <div className="lg:col-span-4">
          <PromptStackField label="内容">
            <Textarea
              className="min-h-[260px] font-mono"
              value={form.content}
              onChange={(event) => onFormChange((prev) => ({ ...prev, content: event.target.value }))}
            />
          </PromptStackField>
        </div>
      </div>
    </section>
  );
}
