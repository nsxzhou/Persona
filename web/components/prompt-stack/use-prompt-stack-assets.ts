"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

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
  ProjectPromptAssetApplySuggestionsRequest,
  ProjectPromptAssetCreate,
  PromptStackPreviewResponse,
} from "@/lib/types";

import {
  EMPTY_PROMPT_ASSET_FORM,
  type PromptStackPreviewContext,
} from "./types";
import {
  normalizePromptAssetForm,
  parseSuggestionArtifact,
} from "./prompt-stack-utils";

const PROMPT_ASSET_SUGGESTIONS_ARTIFACT = "prompt_asset_suggestions";

export function usePromptStackAssets(projectId: string) {
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
  const [form, setForm] = useState<ProjectPromptAssetCreate>(EMPTY_PROMPT_ASSET_FORM);
  const [keywordText, setKeywordText] = useState("");
  const [previewContext, setPreviewContext] = useState<PromptStackPreviewContext>({
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
    setForm(EMPTY_PROMPT_ASSET_FORM);
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

  const saveAsset = async () => {
    const payload = normalizePromptAssetForm(form, keywordText);
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

  const deleteSelectedAsset = async () => {
    if (!selectedId) return;
    await deleteAsset.mutateAsync({ projectId, assetId: selectedId });
    setSelectedId(null);
    setForm(EMPTY_PROMPT_ASSET_FORM);
    setKeywordText("");
    setIsEditorOpen(false);
    toast.success("Prompt 资产已删除");
  };

  const previewAssets = async () => {
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

  const generateSuggestions = async () => {
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

  const applyGeneratedSuggestions = async () => {
    if (!suggestions || suggestions.changes.length === 0) return;
    const payload: ProjectPromptAssetApplySuggestionsRequest = {
      changes: suggestions.changes,
    };
    await applySuggestions.mutateAsync({ projectId, payload });
    setSuggestions(null);
    toast.success("Prompt 资产建议已写回");
  };

  return {
    assets,
    isLoading,
    sortedAssets,
    stats,
    selectedId,
    selectedAsset,
    selectedManifest,
    selectedManifestById,
    form,
    setForm,
    keywordText,
    setKeywordText,
    isEditorOpen,
    isPreviewOpen,
    setIsPreviewOpen,
    isSuggestionsOpen,
    setIsSuggestionsOpen,
    previewContext,
    setPreviewContext,
    preview,
    suggestions,
    isGeneratingSuggestions,
    isSavingAsset: createAsset.isPending || updateAsset.isPending,
    isDeletingAsset: deleteAsset.isPending,
    isPreviewing: previewStack.isPending,
    isApplyingSuggestions: applySuggestions.isPending,
    openNewEditor,
    openExistingEditor,
    closeEditor,
    saveAsset,
    deleteSelectedAsset,
    previewAssets,
    generateSuggestions,
    applyGeneratedSuggestions,
  };
}
