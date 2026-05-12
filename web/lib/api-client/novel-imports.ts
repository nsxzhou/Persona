import type { Requester } from "@/lib/api/requester";
import type {
  NovelImportCommitResponse,
  NovelImportCreatePayload,
  NovelImportPreview,
  NovelImportUpdatePayload,
} from "@/lib/types";

export function createNovelImportApiClient(request: Requester) {
  return {
    previewNovelImport: (payload: NovelImportCreatePayload) => {
      const formData = new FormData();
      formData.append("project_name", payload.project_name);
      formData.append("default_provider_id", payload.default_provider_id);
      if (payload.default_model) formData.append("default_model", payload.default_model);
      if (payload.style_profile_id) formData.append("style_profile_id", payload.style_profile_id);
      if (payload.plot_profile_id) formData.append("plot_profile_id", payload.plot_profile_id);
      if (payload.generation_profile) {
        formData.append("generation_profile", JSON.stringify(payload.generation_profile));
      }
      formData.append("rights_confirmed", String(payload.rights_confirmed));
      formData.append("file", payload.file);

      return request<NovelImportPreview>("/api/v1/novel-imports/preview", {
        method: "POST",
        body: formData,
      });
    },
    updateNovelImport: (draftId: string, payload: NovelImportUpdatePayload) =>
      request<NovelImportPreview>(`/api/v1/novel-imports/${draftId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    commitNovelImport: (draftId: string) =>
      request<NovelImportCommitResponse>(`/api/v1/novel-imports/${draftId}/commit`, {
        method: "POST",
      }),
  };
}
