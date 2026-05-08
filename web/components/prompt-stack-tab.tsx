"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Eye, Plus, Save, Trash2 } from "lucide-react";
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
  useCreateProjectPromptAsset,
  useDeleteProjectPromptAsset,
  usePreviewProjectPromptStack,
  useProjectPromptAssetsQuery,
  useUpdateProjectPromptAsset,
} from "@/hooks/use-project-query";
import type {
  ProjectChapter,
  ProjectPromptAsset,
  ProjectPromptAssetCreate,
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

function normalizeForm(form: ProjectPromptAssetCreate, keywordText: string): ProjectPromptAssetCreate {
  return {
    ...form,
    chapter_id: form.scope === "chapter" ? form.chapter_id : null,
    keywords: keywordText.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean),
    priority: Number(form.priority) || 0,
  };
}

function kindLabel(kind: AssetKind) {
  return KIND_OPTIONS.find((option) => option.value === kind)?.label ?? kind;
}
