import type {
  ProjectPromptAsset,
  ProjectPromptAssetCreate,
  PromptStackPreviewResponse,
} from "@/lib/types";

export type AssetKind = ProjectPromptAsset["kind"];
export type AssetScope = ProjectPromptAsset["scope"];
export type PromptStackAssetManifestItem =
  PromptStackPreviewResponse["manifest"]["selected_assets"][number];
export type PromptStackLayerManifestItem =
  PromptStackPreviewResponse["manifest"]["layers"][number];

export type PromptStackPreviewContext = {
  chapter_id: string;
  current_chapter_context: string;
  text_before_cursor: string;
  user_context: string;
};

export const EMPTY_PROMPT_ASSET_FORM: ProjectPromptAssetCreate = {
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
