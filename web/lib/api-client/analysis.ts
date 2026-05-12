import type { Requester } from "@/lib/api/requester";
import type {
  AnalysisMeta,
  AnalysisReportMarkdown,
  PlotAnalysisJob,
  PlotAnalysisJobCreatePayload,
  PlotAnalysisJobListItem,
  PlotAnalysisJobLogs,
  PlotAnalysisJobStatusSnapshot,
  PlotAnalysisMeta,
  PlotAnalysisReportMarkdown,
  PlotProfile,
  PlotProfileCreatePayload,
  PlotProfileListItem,
  PlotProfileUpdatePayload,
  PlotSkeletonMarkdown,
  StoryEngineMarkdown,
  StyleAnalysisJob,
  StyleAnalysisJobCreatePayload,
  StyleAnalysisJobListItem,
  StyleAnalysisJobLogs,
  StyleAnalysisJobStatusSnapshot,
  StyleProfile,
  StyleProfileCreatePayload,
  StyleProfileListItem,
  StyleProfileUpdatePayload,
  VoiceProfileMarkdown,
} from "@/lib/types";

export function createAnalysisApiClient(request: Requester) {
  return {
    getStyleAnalysisJobs: (params?: { offset?: number; limit?: number }) => {
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<StyleAnalysisJobListItem[]>(
        `/api/v1/style-analysis-jobs?offset=${offset}&limit=${limit}`,
      );
    },
    getStyleAnalysisJobStatus: (id: string) =>
      request<StyleAnalysisJobStatusSnapshot>(`/api/v1/style-analysis-jobs/${id}/status`),
    getStyleAnalysisJob: (id: string) =>
      request<StyleAnalysisJob>(`/api/v1/style-analysis-jobs/${id}`),
    getStyleAnalysisJobLogs: (id: string, offset = 0) =>
      request<StyleAnalysisJobLogs>(`/api/v1/style-analysis-jobs/${id}/logs?offset=${offset}`),
    getStyleAnalysisJobAnalysisMeta: (id: string) =>
      request<AnalysisMeta>(`/api/v1/style-analysis-jobs/${id}/analysis-meta`),
    getStyleAnalysisJobAnalysisReport: (id: string) =>
      request<AnalysisReportMarkdown>(`/api/v1/style-analysis-jobs/${id}/analysis-report`),
    getStyleAnalysisJobVoiceProfile: (id: string) =>
      request<VoiceProfileMarkdown>(`/api/v1/style-analysis-jobs/${id}/voice-profile`),
    resumeStyleAnalysisJob: (id: string) =>
      request<StyleAnalysisJobStatusSnapshot>(`/api/v1/style-analysis-jobs/${id}/resume`, {
        method: "POST",
      }),
    pauseStyleAnalysisJob: (id: string) =>
      request<StyleAnalysisJobStatusSnapshot>(`/api/v1/style-analysis-jobs/${id}/pause`, {
        method: "POST",
      }),
    deleteStyleAnalysisJob: (id: string) =>
      request<void>(`/api/v1/style-analysis-jobs/${id}`, {
        method: "DELETE",
      }),
    createStyleAnalysisJob: (payload: StyleAnalysisJobCreatePayload & { file: File }) => {
      const formData = new FormData();
      formData.append("style_name", payload.style_name);
      formData.append("provider_id", payload.provider_id);
      if (payload.model) {
        formData.append("model", payload.model);
      }
      formData.append("file", payload.file);

      return request<StyleAnalysisJobListItem>("/api/v1/style-analysis-jobs", {
        method: "POST",
        body: formData,
      });
    },
    getStyleProfiles: (params?: { offset?: number; limit?: number }) => {
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<StyleProfileListItem[]>(`/api/v1/style-profiles?offset=${offset}&limit=${limit}`);
    },
    getStyleProfile: (id: string) => request<StyleProfile>(`/api/v1/style-profiles/${id}`),
    createStyleProfile: (payload: StyleProfileCreatePayload) =>
      request<StyleProfile>("/api/v1/style-profiles", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updateStyleProfile: (id: string, payload: StyleProfileUpdatePayload) =>
      request<StyleProfile>(`/api/v1/style-profiles/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    deleteStyleProfile: (id: string) =>
      request<void>(`/api/v1/style-profiles/${id}`, {
        method: "DELETE",
      }),
    getPlotAnalysisJobs: (params?: { offset?: number; limit?: number }) => {
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<PlotAnalysisJobListItem[]>(
        `/api/v1/plot-analysis-jobs?offset=${offset}&limit=${limit}`,
      );
    },
    getPlotAnalysisJobStatus: (id: string) =>
      request<PlotAnalysisJobStatusSnapshot>(`/api/v1/plot-analysis-jobs/${id}/status`),
    getPlotAnalysisJob: (id: string) =>
      request<PlotAnalysisJob>(`/api/v1/plot-analysis-jobs/${id}`),
    getPlotAnalysisJobLogs: (id: string, offset = 0) =>
      request<PlotAnalysisJobLogs>(`/api/v1/plot-analysis-jobs/${id}/logs?offset=${offset}`),
    getPlotAnalysisJobAnalysisMeta: (id: string) =>
      request<PlotAnalysisMeta>(`/api/v1/plot-analysis-jobs/${id}/analysis-meta`),
    getPlotAnalysisJobAnalysisReport: (id: string) =>
      request<PlotAnalysisReportMarkdown>(`/api/v1/plot-analysis-jobs/${id}/analysis-report`),
    getPlotAnalysisJobPlotSkeleton: (id: string) =>
      request<PlotSkeletonMarkdown>(`/api/v1/plot-analysis-jobs/${id}/plot-skeleton`),
    getPlotAnalysisJobStoryEngine: (id: string) =>
      request<StoryEngineMarkdown>(`/api/v1/plot-analysis-jobs/${id}/story-engine`),
    resumePlotAnalysisJob: (id: string) =>
      request<PlotAnalysisJobStatusSnapshot>(`/api/v1/plot-analysis-jobs/${id}/resume`, {
        method: "POST",
      }),
    pausePlotAnalysisJob: (id: string) =>
      request<PlotAnalysisJobStatusSnapshot>(`/api/v1/plot-analysis-jobs/${id}/pause`, {
        method: "POST",
      }),
    deletePlotAnalysisJob: (id: string) =>
      request<void>(`/api/v1/plot-analysis-jobs/${id}`, {
        method: "DELETE",
      }),
    createPlotAnalysisJob: (payload: PlotAnalysisJobCreatePayload & { file: File }) => {
      const formData = new FormData();
      formData.append("plot_name", payload.plot_name);
      formData.append("provider_id", payload.provider_id);
      if (payload.model) {
        formData.append("model", payload.model);
      }
      formData.append("file", payload.file);

      return request<PlotAnalysisJobListItem>("/api/v1/plot-analysis-jobs", {
        method: "POST",
        body: formData,
      });
    },
    getPlotProfiles: (params?: { offset?: number; limit?: number }) => {
      const offset = params?.offset ?? 0;
      const limit = params?.limit ?? 50;
      return request<PlotProfileListItem[]>(`/api/v1/plot-profiles?offset=${offset}&limit=${limit}`);
    },
    getPlotProfile: (id: string) => request<PlotProfile>(`/api/v1/plot-profiles/${id}`),
    createPlotProfile: (payload: PlotProfileCreatePayload) =>
      request<PlotProfile>("/api/v1/plot-profiles", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    updatePlotProfile: (id: string, payload: PlotProfileUpdatePayload) =>
      request<PlotProfile>(`/api/v1/plot-profiles/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    deletePlotProfile: (id: string) =>
      request<void>(`/api/v1/plot-profiles/${id}`, {
        method: "DELETE",
      }),
  };
}
