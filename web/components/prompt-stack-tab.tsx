"use client";

import type { ProjectChapter } from "@/lib/types";

import { PromptAssetEditor } from "./prompt-stack/prompt-asset-editor";
import { PromptAssetSuggestionPanel } from "./prompt-stack/prompt-asset-suggestion-panel";
import {
  EmptyPromptStackState,
  PromptAssetTable,
  PromptStackSummary,
} from "./prompt-stack/prompt-stack-overview";
import { PromptStackPreviewPanel } from "./prompt-stack/prompt-stack-preview-panel";
import { usePromptStackAssets } from "./prompt-stack/use-prompt-stack-assets";

interface PromptStackTabProps {
  projectId: string;
  chapters: ProjectChapter[];
}

export function PromptStackTab({ projectId, chapters }: PromptStackTabProps) {
  const {
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
    isSavingAsset,
    isDeletingAsset,
    isPreviewing,
    isApplyingSuggestions,
    openNewEditor,
    openExistingEditor,
    closeEditor,
    saveAsset,
    deleteSelectedAsset,
    previewAssets,
    generateSuggestions,
    applyGeneratedSuggestions,
  } = usePromptStackAssets(projectId);

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
          onGenerateSuggestions={() => void generateSuggestions()}
          onCreateAsset={openNewEditor}
        />
      ) : (
        <PromptAssetTable
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
        <PromptAssetEditor
          form={form}
          keywordText={keywordText}
          selectedAsset={selectedAsset}
          selectedManifest={selectedManifest}
          chapters={chapters}
          onFormChange={setForm}
          onKeywordTextChange={setKeywordText}
          onSave={() => void saveAsset()}
          onDelete={() => void deleteSelectedAsset()}
          onCancel={closeEditor}
          isSaving={isSavingAsset}
          isDeleting={isDeletingAsset}
        />
      ) : null}

      {assets.length > 0 || suggestions ? (
        <PromptAssetSuggestionPanel
          open={isSuggestionsOpen}
          onOpenChange={setIsSuggestionsOpen}
          suggestions={suggestions}
          assets={assets}
          isGenerating={isGeneratingSuggestions}
          isApplying={isApplyingSuggestions}
          onGenerate={() => void generateSuggestions()}
          onApply={() => void applyGeneratedSuggestions()}
        />
      ) : null}

      <PromptStackPreviewPanel
        open={isPreviewOpen}
        onOpenChange={setIsPreviewOpen}
        preview={preview}
        previewContext={previewContext}
        chapters={chapters}
        assetCount={assets.length}
        isPreviewing={isPreviewing}
        onPreviewContextChange={setPreviewContext}
        onPreview={() => void previewAssets()}
      />
    </div>
  );
}
