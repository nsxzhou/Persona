"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { api } from "@/lib/api";
import type {
  NovelImportPreview,
  NovelImportUpdatePayload,
  PlotProfileListItem,
  ProviderConfig,
  StyleProfileListItem,
} from "@/lib/types";

type ImportTxtDialogProps = {
  open: boolean;
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  plotProfiles: PlotProfileListItem[];
  onOpenChange: (open: boolean) => void;
};

export function ImportTxtDialog({
  open,
  providers,
  styleProfiles,
  plotProfiles,
  onOpenChange,
}: ImportTxtDialogProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const enabledProviders = useMemo(
    () => providers.filter((provider) => provider.is_enabled),
    [providers],
  );
  const [projectName, setProjectName] = useState("");
  const [providerId, setProviderId] = useState("");
  const [defaultModel, setDefaultModel] = useState("");
  const [styleProfileId, setStyleProfileId] = useState("none");
  const [plotProfileId, setPlotProfileId] = useState("none");
  const [rightsConfirmed, setRightsConfirmed] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<NovelImportPreview | null>(null);

  const selectedProvider = enabledProviders.find((provider) => provider.id === providerId);
  const resolvedDefaultModel = defaultModel.trim() || selectedProvider?.default_model || "";

  useEffect(() => {
    if (!open || providerId || enabledProviders.length === 0) return;
    setProviderId(enabledProviders[0].id);
    setDefaultModel(enabledProviders[0].default_model);
  }, [enabledProviders, open, providerId]);

  const reset = () => {
    setProjectName("");
    setProviderId("");
    setDefaultModel("");
    setStyleProfileId("none");
    setPlotProfileId("none");
    setRightsConfirmed(false);
    setFile(null);
    setPreview(null);
  };

  const previewMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("请选择 TXT 文件");
      return api.previewNovelImport({
        project_name: projectName.trim(),
        default_provider_id: providerId,
        default_model: resolvedDefaultModel,
        style_profile_id: styleProfileId === "none" ? undefined : styleProfileId,
        plot_profile_id: plotProfileId === "none" ? undefined : plotProfileId,
        rights_confirmed: rightsConfirmed,
        file,
      });
    },
    onSuccess: (data) => {
      setPreview(data);
      setProjectName(data.project.project_name);
      setProviderId(data.project.default_provider_id);
      setDefaultModel(data.project.default_model ?? "");
      setStyleProfileId(data.project.style_profile_id ?? "none");
      setPlotProfileId(data.project.plot_profile_id ?? "none");
      toast.success("TXT 解析完成");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "TXT 解析失败"),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: NovelImportUpdatePayload) => {
      if (!preview) throw new Error("缺少导入草稿");
      return api.updateNovelImport(preview.draft_id, payload);
    },
    onSuccess: (data) => {
      setPreview(data);
      setProjectName(data.project.project_name);
      setProviderId(data.project.default_provider_id);
      setDefaultModel(data.project.default_model ?? "");
      setStyleProfileId(data.project.style_profile_id ?? "none");
      setPlotProfileId(data.project.plot_profile_id ?? "none");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "草稿更新失败"),
  });

  const commitMutation = useMutation({
    mutationFn: () => {
      if (!preview) throw new Error("请先解析 TXT");
      return api.commitNovelImport(preview.draft_id);
    },
    onSuccess: async (data) => {
      toast.success("导入项目已创建");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      reset();
      onOpenChange(false);
      router.push(`/projects/${data.project_id}/editor`);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "导入提交失败"),
  });

  const canPreview = Boolean(projectName.trim() && providerId && file && rightsConfirmed);
  const isBusy = previewMutation.isPending || updateMutation.isPending || commitMutation.isPending;

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen && isBusy) return;
    if (!nextOpen) reset();
    onOpenChange(nextOpen);
  };

  const updateChapter = (index: number, field: "title" | "content", value: string) => {
    if (!preview) return;
    const nextChapters = preview.chapters.map((chapter, chapterIndex) =>
      chapterIndex === index
        ? {
            ...chapter,
            [field]: value,
            word_count: field === "content" ? value.length : chapter.word_count,
          }
        : chapter,
    );
    setPreview({ ...preview, chapters: nextChapters });
  };

  const syncDraft = () => {
    if (!preview) return;
    updateMutation.mutate({
      project: {
        ...preview.project,
        project_name: projectName.trim() || preview.project.project_name,
        default_provider_id: providerId || preview.project.default_provider_id,
        default_model: resolvedDefaultModel,
        style_profile_id: styleProfileId === "none" ? null : styleProfileId,
        plot_profile_id: plotProfileId === "none" ? null : plotProfileId,
      },
      chapters: preview.chapters,
    });
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-5xl overflow-hidden">
        <DialogHeader>
          <DialogTitle>导入 TXT 小说</DialogTitle>
          <DialogDescription>
            上传你有权处理的 TXT，确认解析结果后创建项目。
          </DialogDescription>
        </DialogHeader>

        <div className="grid max-h-[68vh] gap-5 overflow-y-auto pr-1 lg:grid-cols-[320px_1fr]">
          <section className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="txt-project-name">项目名称</Label>
              <Input
                id="txt-project-name"
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                disabled={isBusy}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="txt-provider">Provider</Label>
              <Select
                value={providerId}
                onValueChange={(value) => {
                  setProviderId(value);
                  const provider = enabledProviders.find((item) => item.id === value);
                  setDefaultModel(provider?.default_model ?? "");
                }}
                disabled={isBusy}
              >
                <SelectTrigger id="txt-provider">
                  <SelectValue placeholder="选择 Provider" />
                </SelectTrigger>
                <SelectContent>
                  {enabledProviders.map((provider) => (
                    <SelectItem key={provider.id} value={provider.id}>
                      {provider.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="txt-default-model">模型</Label>
              <Input
                id="txt-default-model"
                value={defaultModel}
                onChange={(event) => setDefaultModel(event.target.value)}
                placeholder={selectedProvider?.default_model ?? ""}
                disabled={isBusy}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="txt-style-profile">风格档案</Label>
              <Select value={styleProfileId} onValueChange={setStyleProfileId} disabled={isBusy}>
                <SelectTrigger id="txt-style-profile">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">不挂载</SelectItem>
                  {styleProfiles.map((profile) => (
                    <SelectItem key={profile.id} value={profile.id}>
                      {profile.style_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="txt-plot-profile">剧情档案</Label>
              <Select value={plotProfileId} onValueChange={setPlotProfileId} disabled={isBusy}>
                <SelectTrigger id="txt-plot-profile">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">不挂载</SelectItem>
                  {plotProfiles.map((profile) => (
                    <SelectItem key={profile.id} value={profile.id}>
                      {profile.plot_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="txt-file">TXT 文件</Label>
              <Input
                id="txt-file"
                type="file"
                accept=".txt,text/plain"
                disabled={isBusy}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </div>

            <label className="flex items-start gap-2 rounded-md border border-border p-3 text-sm">
              <Checkbox
                checked={rightsConfirmed}
                onCheckedChange={(value) => setRightsConfirmed(value === true)}
                disabled={isBusy}
              />
              <span>我确认拥有处理该 TXT 内容并创建改写项目的权利。</span>
            </label>

            <Button
              className="w-full gap-2"
              onClick={() => previewMutation.mutate()}
              disabled={!canPreview || isBusy}
            >
              {previewMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
              解析预览
            </Button>
          </section>

          <section className="min-h-[420px] space-y-4">
            {!preview ? (
              <div className="flex h-full min-h-[420px] items-center justify-center rounded-md border border-dashed border-border text-sm text-muted-foreground">
                解析后可在这里编辑章节标题和正文。
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-muted/30 p-3">
                  <div>
                    <p className="text-sm font-medium">
                      已解析 {preview.chapters.length} 章
                    </p>
                    <p className="text-xs text-muted-foreground">
                      共 {preview.chapters.reduce((sum, chapter) => sum + chapter.word_count, 0).toLocaleString()} 字
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(preview.warnings ?? []).includes("no_standard_chapter_headings") ? (
                      <Badge variant="outline">未识别标准章节标题，已作为单章导入</Badge>
                    ) : null}
                  </div>
                </div>

                <div className="space-y-3">
                  {preview.chapters.map((chapter, index) => (
                    <div key={chapter.client_id} className="space-y-2 rounded-md border border-border p-3">
                      <div className="grid gap-2 md:grid-cols-[1fr_110px] md:items-center">
                        <Input
                          value={chapter.title}
                          onChange={(event) => updateChapter(index, "title", event.target.value)}
                          disabled={isBusy}
                          aria-label={`第 ${index + 1} 章标题`}
                        />
                        <span className="text-xs text-muted-foreground md:text-right">
                          {chapter.word_count.toLocaleString()} 字
                        </span>
                      </div>
                      <Textarea
                        value={chapter.content}
                        onChange={(event) => updateChapter(index, "content", event.target.value)}
                        disabled={isBusy}
                        className="min-h-40 leading-relaxed"
                        aria-label={`第 ${index + 1} 章正文`}
                      />
                    </div>
                  ))}
                </div>
              </>
            )}
          </section>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isBusy}>
            取消
          </Button>
          <Button variant="outline" onClick={syncDraft} disabled={!preview || isBusy}>
            保存草稿
          </Button>
          <Button onClick={() => commitMutation.mutate()} disabled={!preview || isBusy}>
            {commitMutation.isPending ? "创建中..." : "创建项目"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
