"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Check,
  ChevronDown,
  ChevronRight,
  Eye,
  FileText,
  Layers3,
  Pencil,
  Plus,
  Save,
  Search,
  Sparkles,
  Trash2,
  WandSparkles,
} from "lucide-react";
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
import { cn } from "@/lib/utils";
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
type PromptStackAssetManifestItem =
  PromptStackPreviewResponse["manifest"]["selected_assets"][number];
type PromptStackLayerManifestItem =
  PromptStackPreviewResponse["manifest"]["layers"][number];

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
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isSuggestionsOpen, setIsSuggestionsOpen] = useState(false);
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

  const stats = useMemo(() => {
    const enabled = assets.filter((asset) => asset.enabled).length;
    const alwaysOn = assets.filter((asset) => asset.enabled && asset.always_on).length;
    const keywordTriggered = assets.filter(
      (asset) => asset.enabled && !asset.always_on && asset.keywords.length > 0,
    ).length;
    return { enabled, alwaysOn, keywordTriggered };
  }, [assets]);

  const selectedManifestById = useMemo(() => {
    const entries = preview?.manifest.selected_assets ?? [];
    return new Map(entries.map((asset) => [asset.id, asset]));
  }, [preview]);

  const selectedManifest = selectedAsset ? selectedManifestById.get(selectedAsset.id) : undefined;

  const openNewEditor = () => {
    setSelectedId(null);
    setForm(EMPTY_FORM);
    setKeywordText("");
    setIsEditorOpen(true);
  };

  const openExistingEditor = (assetId: string) => {
    setSelectedId(assetId);
    setIsEditorOpen(true);
  };

  const closeEditor = () => {
    setIsEditorOpen(false);
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
    setIsEditorOpen(true);
    toast.success("Prompt 资产已创建");
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    await deleteAsset.mutateAsync({ projectId, assetId: selectedId });
    setSelectedId(null);
    setForm(EMPTY_FORM);
    setKeywordText("");
    setIsEditorOpen(false);
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
    setIsSuggestionsOpen(true);
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
    <div className="mx-auto max-w-6xl space-y-5">
      <PromptStackSummary
        assetCount={assets.length}
        enabledCount={stats.enabled}
        alwaysOnCount={stats.alwaysOn}
        keywordTriggeredCount={stats.keywordTriggered}
      />

      {!isLoading && assets.length === 0 ? (
        <EmptyPromptStackState
          isGeneratingSuggestions={isGeneratingSuggestions}
          onGenerateSuggestions={() => void handleGenerateSuggestions()}
          onCreateAsset={openNewEditor}
        />
      ) : (
        <AssetTable
          assets={sortedAssets}
          isLoading={isLoading}
          selectedId={selectedId}
          selectedManifestById={selectedManifestById}
          hasPreview={Boolean(preview)}
          onCreateAsset={openNewEditor}
          onEditAsset={openExistingEditor}
        />
      )}

      {isEditorOpen ? (
        <AssetEditor
          form={form}
          keywordText={keywordText}
          selectedAsset={selectedAsset}
          selectedManifest={selectedManifest}
          chapters={chapters}
          onFormChange={setForm}
          onKeywordTextChange={setKeywordText}
          onSave={() => void handleSave()}
          onDelete={() => void handleDelete()}
          onCancel={closeEditor}
          isSaving={createAsset.isPending || updateAsset.isPending}
          isDeleting={deleteAsset.isPending}
        />
      ) : null}

      {assets.length > 0 || suggestions ? (
        <SuggestionPanel
          open={isSuggestionsOpen}
          onOpenChange={setIsSuggestionsOpen}
          suggestions={suggestions}
          assets={assets}
          isGenerating={isGeneratingSuggestions}
          isApplying={applySuggestions.isPending}
          onGenerate={() => void handleGenerateSuggestions()}
          onApply={() => void handleApplySuggestions()}
        />
      ) : null}

      <PreviewPanel
        open={isPreviewOpen}
        onOpenChange={setIsPreviewOpen}
        preview={preview}
        previewContext={previewContext}
        chapters={chapters}
        assetCount={assets.length}
        isPreviewing={previewStack.isPending}
        onPreviewContextChange={setPreviewContext}
        onPreview={() => void handlePreview()}
      />
    </div>
  );
}

function PromptStackSummary({
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

function EmptyPromptStackState({
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

function AssetTable({
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

function AssetEditor({
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
  onFormChange: (next: ProjectPromptAssetCreate | ((prev: ProjectPromptAssetCreate) => ProjectPromptAssetCreate)) => void;
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
        <Field label="类型">
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
        </Field>
        <Field label="作用域">
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
        </Field>
        {form.scope === "chapter" ? (
          <Field label="章节">
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
          </Field>
        ) : null}
        <Field label="优先级">
          <Input
            type="number"
            value={String(form.priority)}
            onChange={(event) =>
              onFormChange((prev) => ({ ...prev, priority: Number(event.target.value) || 0 }))
            }
          />
        </Field>
        <div className="lg:col-span-2">
          <Field label="标题">
            <Input
              value={form.title}
              onChange={(event) => onFormChange((prev) => ({ ...prev, title: event.target.value }))}
            />
          </Field>
        </div>
        <div className="lg:col-span-2">
          <Field label="关键词">
            <Input
              value={keywordText}
              onChange={(event) => onKeywordTextChange(event.target.value)}
              placeholder="逗号分隔"
            />
          </Field>
        </div>
        <div className="flex flex-wrap items-center gap-6 lg:col-span-4">
          <SwitchField
            label="启用"
            checked={form.enabled}
            onCheckedChange={(checked) => onFormChange((prev) => ({ ...prev, enabled: checked }))}
          />
          <SwitchField
            label="Always-on"
            checked={form.always_on}
            onCheckedChange={(checked) =>
              onFormChange((prev) => ({ ...prev, always_on: checked }))
            }
          />
        </div>
        <div className="lg:col-span-4">
          <Field label="内容">
            <Textarea
              className="min-h-[260px] font-mono"
              value={form.content}
              onChange={(event) => onFormChange((prev) => ({ ...prev, content: event.target.value }))}
            />
          </Field>
        </div>
      </div>
    </section>
  );
}

function SuggestionPanel({
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
    <CollapsiblePanel
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
        <EmptyPanel
          title="尚未生成建议"
          description="点击生成后，建议会按新增、更新、禁用分组展示。"
        />
      )}
    </CollapsiblePanel>
  );
}

function PreviewPanel({
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
  previewContext: {
    chapter_id: string;
    current_chapter_context: string;
    text_before_cursor: string;
    user_context: string;
  };
  chapters: ProjectChapter[];
  assetCount: number;
  isPreviewing: boolean;
  onPreviewContextChange: (
    next:
      | typeof previewContext
      | ((prev: typeof previewContext) => typeof previewContext),
  ) => void;
  onPreview: () => void;
}) {
  return (
    <CollapsiblePanel
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
          <Field label="预览章节">
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
          </Field>
          <Field label="当前章节上下文">
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
          </Field>
          <Field label="光标前正文">
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
          </Field>
          <Field label="用户上下文">
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
          </Field>
          <Button type="button" className="w-full" onClick={onPreview} disabled={isPreviewing}>
            <Eye className="mr-1.5 h-4 w-4" />
            {isPreviewing ? "预览中..." : "预览注入结果"}
          </Button>
        </div>

        <PromptStackDiagnostics preview={preview} assetCount={assetCount} />
      </div>
    </CollapsiblePanel>
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
      <EmptyPanel
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
          <EmptyPanel
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
            {formatChars(preview.manifest.final_prompt_char_count)}
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
            {assets.length} 项资产 · {formatChars(layer.char_count)}
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
        <EmptyPanel title="没有需要写回的建议" description="当前资产库不需要调整。" />
      ) : null}
    </div>
  );
}

function CollapsiblePanel({
  title,
  description,
  icon,
  open,
  onOpenChange,
  rightSlot,
  children,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rightSlot?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border-2 bg-card">
      <div className="flex items-center justify-between gap-4 p-4">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-start gap-3 text-left"
          onClick={() => onOpenChange(!open)}
        >
          <div className="mt-0.5">{icon}</div>
          <div className="min-w-0">
            <div className="font-semibold">{title}</div>
            <div className="mt-1 text-sm leading-5 text-muted-foreground">{description}</div>
          </div>
        </button>
        <div className="flex shrink-0 items-center gap-3">
          {rightSlot}
          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-md border-2 hover:bg-accent"
            onClick={() => onOpenChange(!open)}
            aria-label={open ? `收起${title}` : `展开${title}`}
          >
            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
        </div>
      </div>
      {open ? <div className="border-t-2 p-4">{children}</div> : null}
    </section>
  );
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

function EmptyPanel({
  icon,
  title,
  description,
}: {
  icon?: ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border-2 border-dashed p-4 text-sm text-muted-foreground">
      <div className="flex items-center gap-2 font-medium text-foreground">
        {icon}
        {title}
      </div>
      <p className="mt-2 leading-6">{description}</p>
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
    <label className="flex min-h-11 items-center gap-2 text-sm">
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
      <span>{label}</span>
    </label>
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

function scopeLabel(scope: AssetScope) {
  return SCOPE_OPTIONS.find((option) => option.value === scope)?.label ?? scope;
}

function reasonLabel(reason: string) {
  if (reason === "always_on") return "Always-on";
  if (reason === "keyword") return "关键词";
  return reason;
}

function layerTitleLabel(title: string) {
  if (title === "Active Lorebook Entries") return "世界书";
  if (title === "Active Character Cards") return "角色卡";
  if (title === "Author Notes") return "作者注释";
  return title;
}

function formatChars(value: number) {
  return `${value.toLocaleString()} 字符`;
}
