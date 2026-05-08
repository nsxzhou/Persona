"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Check, Eye, Plus, Save, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  useApplyProjectPromptAssetSuggestions,
  useCreateProjectPromptAsset,
  useDeleteProjectPromptAsset,
  usePreviewProjectPromptStack,
  useProjectPromptAssetsQuery,
  useUpdateProjectPromptAsset,
} from "@/hooks/use-project-query";
import { api } from "@/lib/api";
import type {
  PromptAssetInitSuggestionsResponse,
  ProjectChapter,
  ProjectPromptAsset,
  ProjectPromptAssetApplySuggestionsRequest,
  ProjectPromptAssetCreate,
  ProjectPromptAssetSuggestionChange,
  PromptStackPreviewResponse,
} from "@/lib/types";

type AssetKind = ProjectPromptAsset["kind"];
type AssetScope = ProjectPromptAsset["scope"];

const KIND_OPTIONS: { value: AssetKind; label: string }[] = [
  { value: "lorebook_entry", label: "世界书" },
  { value: "character_card", label: "角色卡" },
  { value: "author_note", label: "作者注释" },
];

const SCOPE_OPTIONS: { value: AssetScope; label: string }[] = [
  { value: "project", label: "项目" },
  { value: "chapter", label: "章节" },
];

const EMPTY_FORM: ProjectPromptAssetCreate = {
  kind: "lorebook_entry",
  scope: "project",
  chapter_id: null,
  title: "",
  content: "",
  keywords: [],
  enabled: true,
  always_on: false,
  priority: 0,
};
const ALL_CHAPTERS_PREVIEW_VALUE = "__all_chapters__";
const PROMPT_ASSET_SUGGESTIONS_ARTIFACT = "prompt_asset_suggestions";

interface PromptStackTabProps {
  projectId: string;
  chapters: ProjectChapter[];
}

export function PromptStackTab({ projectId, chapters }: PromptStackTabProps) {
  const { data: assets = [], isLoading } = useProjectPromptAssetsQuery(projectId);
  const createAsset = useCreateProjectPromptAsset();
  const updateAsset = useUpdateProjectPromptAsset();
  const deleteAsset = useDeleteProjectPromptAsset();
  const previewStack = usePreviewProjectPromptStack();
  const applySuggestions = useApplyProjectPromptAssetSuggestions();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<ProjectPromptAssetCreate>(EMPTY_FORM);
  const [keywordText, setKeywordText] = useState("");
  const [previewContext, setPreviewContext] = useState({
    chapter_id: "",
    current_chapter_context: "",
    text_before_cursor: "",
    user_context: "",
  });
  const [preview, setPreview] = useState<PromptStackPreviewResponse | null>(null);
  const [suggestions, setSuggestions] = useState<PromptAssetInitSuggestionsResponse | null>(null);
  const [isGeneratingSuggestions, setIsGeneratingSuggestions] = useState(false);

  const selectedAsset = assets.find((asset) => asset.id === selectedId) ?? null;

  useEffect(() => {
    if (!selectedAsset) return;
    setForm({
      kind: selectedAsset.kind,
      scope: selectedAsset.scope,
      chapter_id: selectedAsset.chapter_id,
      title: selectedAsset.title,
      content: selectedAsset.content,
      keywords: selectedAsset.keywords,
      enabled: selectedAsset.enabled,
      always_on: selectedAsset.always_on,
      priority: selectedAsset.priority,
    });
    setKeywordText(selectedAsset.keywords.join(", "));
  }, [selectedAsset]);

  const sortedAssets = useMemo(
    () => [...assets].sort((a, b) => b.priority - a.priority || a.title.localeCompare(b.title)),
    [assets],
  );

  const handleNew = () => {
    setSelectedId(null);
    setForm(EMPTY_FORM);
    setKeywordText("");
  };

  const handleSave = async () => {
    const payload = normalizeForm(form, keywordText);
    if (!payload.title.trim()) {
      toast.error("请输入资产标题");
      return;
    }
    if (payload.scope === "chapter" && !payload.chapter_id) {
      toast.error("章节级资产需要选择章节");
      return;
    }
    if (selectedId) {
      await updateAsset.mutateAsync({ projectId, assetId: selectedId, payload });
      toast.success("Prompt 资产已保存");
      return;
    }
    const created = await createAsset.mutateAsync({ projectId, payload });
    setSelectedId(created.id);
    toast.success("Prompt 资产已创建");
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    await deleteAsset.mutateAsync({ projectId, assetId: selectedId });
    handleNew();
    toast.success("Prompt 资产已删除");
  };

  const handlePreview = async () => {
    const result = await previewStack.mutateAsync({
      projectId,
      payload: {
        chapter_id: previewContext.chapter_id || null,
        current_chapter_context: previewContext.current_chapter_context,
        text_before_cursor: previewContext.text_before_cursor,
        user_context: previewContext.user_context,
      },
    });
    setPreview(result);
  };

  const handleGenerateSuggestions = async () => {
    setIsGeneratingSuggestions(true);
    try {
      const run = await api.createNovelWorkflow({
        intent_type: "prompt_asset_init",
        project_id: projectId,
      } as Parameters<typeof api.createNovelWorkflow>[0]);
      const status = await api.waitForNovelWorkflow(run.id);
      if (status.status === "failed") {
        throw new Error(status.error_message || "Prompt 资产初始化失败");
      }
      const artifact = await api.getNovelWorkflowArtifact(run.id, PROMPT_ASSET_SUGGESTIONS_ARTIFACT);
      const parsed = parseSuggestionArtifact(artifact);
      setSuggestions(parsed);
      toast.success("Prompt 资产建议已生成");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Prompt 资产建议生成失败");
    } finally {
      setIsGeneratingSuggestions(false);
    }
  };

  const handleApplySuggestions = async () => {
    if (!suggestions || suggestions.changes.length === 0) return;
    const payload: ProjectPromptAssetApplySuggestionsRequest = {
      changes: suggestions.changes,
    };
    await applySuggestions.mutateAsync({ projectId, payload });
    setSuggestions(null);
    toast.success("Prompt 资产建议已写回");
  };

  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Prompt 资产</h2>
          <Button type="button" size="sm" variant="outline" onClick={handleNew}>
            <Plus className="mr-1.5 h-4 w-4" />
            新建
          </Button>
        </div>
        <div className="space-y-2">
          {isLoading ? <p className="text-sm text-muted-foreground">正在加载...</p> : null}
          {sortedAssets.map((asset) => (
            <button
              key={asset.id}
              type="button"
              onClick={() => setSelectedId(asset.id)}
              className={`w-full rounded-md border-2 p-3 text-left text-sm transition-colors ${
                selectedId === asset.id ? "border-primary bg-accent" : "border-border hover:bg-accent"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{asset.title}</span>
                <Badge variant={asset.enabled ? "secondary" : "outline"}>
                  {asset.enabled ? "启用" : "禁用"}
                </Badge>
              </div>
              <div className="mt-2 flex flex-wrap gap-1 text-xs text-muted-foreground">
                <span>{kindLabel(asset.kind)}</span>
                <span>Priority {asset.priority}</span>
                {asset.always_on ? <span>Always-on</span> : null}
              </div>
            </button>
          ))}
          {!isLoading && sortedAssets.length === 0 ? (
            <p className="rounded-md border-2 border-dashed p-4 text-sm text-muted-foreground">
              暂无 Prompt 资产。
            </p>
          ) : null}
        </div>
      </div>

      <div className="space-y-6">
        <div className="grid gap-4 rounded-md border-2 p-4 md:grid-cols-2">
          <Field label="类型">
            <Select value={form.kind} onValueChange={(value: AssetKind) => setForm((prev) => ({ ...prev, kind: value }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {KIND_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <Field label="作用域">
            <Select value={form.scope} onValueChange={(value: AssetScope) => setForm((prev) => ({ ...prev, scope: value, chapter_id: value === "project" ? null : prev.chapter_id }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {SCOPE_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          {form.scope === "chapter" ? (
            <Field label="章节">
              <Select value={form.chapter_id ?? ""} onValueChange={(value) => setForm((prev) => ({ ...prev, chapter_id: value }))}>
                <SelectTrigger><SelectValue placeholder="选择章节" /></SelectTrigger>
                <SelectContent>
                  {chapters.map((chapter) => (
                    <SelectItem key={chapter.id} value={chapter.id}>{chapter.title || `第 ${chapter.chapter_index + 1} 章`}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          ) : null}
          <Field label="优先级">
            <Input
              type="number"
              value={String(form.priority)}
              onChange={(event) => setForm((prev) => ({ ...prev, priority: Number(event.target.value) || 0 }))}
            />
          </Field>
          <Field label="标题">
            <Input value={form.title} onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))} />
          </Field>
          <Field label="关键词">
            <Input value={keywordText} onChange={(event) => setKeywordText(event.target.value)} placeholder="逗号分隔" />
          </Field>
          <div className="flex items-center gap-6">
            <SwitchField label="启用" checked={form.enabled} onCheckedChange={(checked) => setForm((prev) => ({ ...prev, enabled: checked }))} />
            <SwitchField label="Always-on" checked={form.always_on} onCheckedChange={(checked) => setForm((prev) => ({ ...prev, always_on: checked }))} />
          </div>
          <div className="md:col-span-2">
            <Field label="内容">
              <Textarea
                className="min-h-[220px] font-mono"
                value={form.content}
                onChange={(event) => setForm((prev) => ({ ...prev, content: event.target.value }))}
              />
            </Field>
          </div>
          <div className="flex gap-2 md:col-span-2">
            <Button type="button" onClick={() => void handleSave()} disabled={createAsset.isPending || updateAsset.isPending}>
              <Save className="mr-1.5 h-4 w-4" />
              保存
            </Button>
            <Button type="button" variant="destructive" onClick={() => void handleDelete()} disabled={!selectedId || deleteAsset.isPending}>
              <Trash2 className="mr-1.5 h-4 w-4" />
              删除
            </Button>
          </div>
        </div>

        <div className="grid gap-4 rounded-md border-2 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-base font-semibold">资产初始化建议</h2>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => void handleGenerateSuggestions()}
                disabled={isGeneratingSuggestions}
              >
                <Sparkles className="mr-1.5 h-4 w-4" />
                生成建议
              </Button>
              <Button
                type="button"
                onClick={() => void handleApplySuggestions()}
                disabled={!suggestions?.changes.length || applySuggestions.isPending}
              >
                <Check className="mr-1.5 h-4 w-4" />
                确认写回
              </Button>
            </div>
          </div>
          {suggestions ? (
            <PromptAssetSuggestions
              changes={suggestions.changes}
              assets={assets}
            />
          ) : (
            <p className="rounded-md border-2 border-dashed p-3 text-sm text-muted-foreground">
              尚未生成初始化建议。
            </p>
          )}
        </div>

        <div className="grid gap-4 rounded-md border-2 p-4">
          <h2 className="text-base font-semibold">Stack 预览</h2>
          <Field label="预览章节">
            <Select
              value={previewContext.chapter_id || ALL_CHAPTERS_PREVIEW_VALUE}
              onValueChange={(value) =>
                setPreviewContext((prev) => ({
                  ...prev,
                  chapter_id: value === ALL_CHAPTERS_PREVIEW_VALUE ? "" : value,
                }))
              }
            >
              <SelectTrigger><SelectValue placeholder="不限定章节" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_CHAPTERS_PREVIEW_VALUE}>不限定章节</SelectItem>
                {chapters.map((chapter) => (
                  <SelectItem key={chapter.id} value={chapter.id}>{chapter.title || `第 ${chapter.chapter_index + 1} 章`}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="当前章节上下文">
            <Textarea value={previewContext.current_chapter_context} onChange={(event) => setPreviewContext((prev) => ({ ...prev, current_chapter_context: event.target.value }))} />
          </Field>
          <Field label="光标前正文">
            <Textarea value={previewContext.text_before_cursor} onChange={(event) => setPreviewContext((prev) => ({ ...prev, text_before_cursor: event.target.value }))} />
          </Field>
          <Field label="用户上下文">
            <Textarea value={previewContext.user_context} onChange={(event) => setPreviewContext((prev) => ({ ...prev, user_context: event.target.value }))} />
          </Field>
          <Button type="button" variant="outline" onClick={() => void handlePreview()} disabled={previewStack.isPending}>
            <Eye className="mr-1.5 h-4 w-4" />
            预览
          </Button>
          {preview ? <PromptStackPreview preview={preview} /> : null}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function SwitchField({
  label,
  checked,
  onCheckedChange,
}: {
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
      {label}
    </label>
  );
}

function PromptStackPreview({ preview }: { preview: PromptStackPreviewResponse }) {
  return (
    <div className="grid gap-4">
      <div className="rounded-md border-2 bg-muted/30 p-3">
        <div className="mb-2 text-sm font-medium">Layer Manifest</div>
        <div className="space-y-2">
          {preview.manifest.layers.map((layer) => (
            <div key={layer.key} className="flex flex-wrap items-center gap-2 text-sm">
              <Badge variant="outline">{layer.title}</Badge>
              <span>{layer.char_count} chars</span>
              {layer.truncated ? <span className="text-destructive">truncated</span> : null}
              {(layer.assets ?? []).map((asset) => <span key={asset.id}>{asset.title}</span>)}
            </div>
          ))}
        </div>
      </div>
      <pre className="max-h-[420px] overflow-auto rounded-md border-2 bg-background p-3 text-xs whitespace-pre-wrap">
        {preview.prompt || "未选中任何资产。"}
      </pre>
    </div>
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
                      {change.asset_id ? <span className="text-xs text-muted-foreground">{change.asset_id}</span> : null}
                    </div>
                    {change.rationale ? (
                      <p className="mt-2 text-xs text-muted-foreground">{change.rationale}</p>
                    ) : null}
                    {payload ? (
                      <div className="mt-2 grid gap-2">
                        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                          <span>Priority {payload.priority}</span>
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
        <p className="rounded-md border-2 border-dashed p-3 text-sm text-muted-foreground">
          没有需要写回的建议。
        </p>
      ) : null}
    </div>
  );
}

function normalizeForm(form: ProjectPromptAssetCreate, keywordText: string): ProjectPromptAssetCreate {
  return {
    ...form,
    chapter_id: form.scope === "chapter" ? form.chapter_id : null,
    keywords: keywordText.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean),
    priority: Number(form.priority) || 0,
  };
}

function parseSuggestionArtifact(markdown: string): PromptAssetInitSuggestionsResponse {
  const trimmed = markdown.trim();
  const fenced = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/);
  const rawJson = fenced ? fenced[1] : trimmed;
  const parsed = JSON.parse(rawJson) as PromptAssetInitSuggestionsResponse;
  return {
    changes: Array.isArray(parsed.changes) ? parsed.changes : [],
  };
}

function actionLabel(action: ProjectPromptAssetSuggestionChange["action"]) {
  if (action === "new") return "新增";
  if (action === "update") return "更新";
  return "禁用";
}

function kindLabel(kind: AssetKind) {
  return KIND_OPTIONS.find((option) => option.value === kind)?.label ?? kind;
}
