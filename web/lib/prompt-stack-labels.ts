import type { ProjectPromptAsset, ProjectPromptAssetSuggestionChange } from "@/lib/types";

type AssetKind = ProjectPromptAsset["kind"];
type AssetScope = ProjectPromptAsset["scope"];

export const PROMPT_ASSET_KIND_OPTIONS: { value: AssetKind; label: string }[] = [
  { value: "lorebook_entry", label: "世界书" },
  { value: "character_card", label: "角色卡" },
  { value: "author_note", label: "作者注释" },
];

export const PROMPT_ASSET_SCOPE_OPTIONS: { value: AssetScope; label: string }[] = [
  { value: "project", label: "项目" },
  { value: "chapter", label: "章节" },
];

export function actionLabel(action: ProjectPromptAssetSuggestionChange["action"]) {
  if (action === "new") return "新增";
  if (action === "update") return "更新";
  return "禁用";
}

export function kindLabel(kind: string) {
  return PROMPT_ASSET_KIND_OPTIONS.find((option) => option.value === kind)?.label ?? kind;
}

export function scopeLabel(scope: string) {
  return PROMPT_ASSET_SCOPE_OPTIONS.find((option) => option.value === scope)?.label ?? scope;
}

export function reasonLabel(reason: string) {
  if (reason === "always_on") return "Always-on";
  if (reason === "keyword") return "关键词";
  return reason;
}

export function layerTitleLabel(title: string) {
  if (title === "Active Lorebook Entries") return "世界书";
  if (title === "Active Character Cards") return "角色卡";
  if (title === "Author Notes") return "作者注释";
  return title;
}
