import type { PromptAssetInitSuggestionsResponse, ProjectPromptAssetCreate } from "@/lib/types";

export function normalizePromptAssetForm(
  form: ProjectPromptAssetCreate,
  keywordText: string,
): ProjectPromptAssetCreate {
  return {
    ...form,
    chapter_id: form.scope === "chapter" ? form.chapter_id : null,
    keywords: keywordText.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean),
    priority: Number(form.priority) || 0,
  };
}

export function parseSuggestionArtifact(markdown: string): PromptAssetInitSuggestionsResponse {
  const trimmed = markdown.trim();
  const fenced = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/);
  const rawJson = fenced ? fenced[1] : trimmed;
  const parsed = JSON.parse(rawJson) as PromptAssetInitSuggestionsResponse;
  return {
    changes: Array.isArray(parsed.changes) ? parsed.changes : [],
  };
}

export function formatPromptStackChars(value: number) {
  return `${value.toLocaleString()} 字符`;
}
