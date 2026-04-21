import type { components } from "@/lib/api/generated/openapi";

type OpenApiSchema<Name extends keyof components["schemas"]> = components["schemas"][Name];

export type User = OpenApiSchema<"UserResponse">;
export type ProviderConfig = OpenApiSchema<"ProviderConfigResponse">;
export type Project = OpenApiSchema<"ProjectResponse">;
export type ProjectSummary = Omit<
  Project,
  | "inspiration"
  | "world_building"
  | "characters"
  | "outline_master"
  | "outline_detail"
  | "runtime_state"
  | "runtime_threads"
>;
export type MemorySyncStatus = "checking" | "pending_review" | "synced" | "no_change" | "failed";
export type MemorySyncSource = "auto" | "manual";
export type MemorySyncScope = "generated_fragment" | "chapter_full";

export type ChapterMemorySyncSnapshot = {
  memory_sync_status: MemorySyncStatus | null;
  memory_sync_source: MemorySyncSource | null;
  memory_sync_scope: MemorySyncScope | null;
  memory_sync_checked_at: string | null;
  memory_sync_checked_content_hash: string | null;
  memory_sync_error_message: string | null;
  memory_sync_proposed_state: string | null;
  memory_sync_proposed_threads: string | null;
};

export type ProjectChapter = OpenApiSchema<"ProjectChapterResponse"> & ChapterMemorySyncSnapshot;

export type AnalysisMeta = OpenApiSchema<"AnalysisMeta">;
export type AnalysisReportMarkdown = OpenApiSchema<"AnalysisReportMarkdown">;
export type StyleSummaryMarkdown = OpenApiSchema<"StyleSummaryMarkdown">;
export type PromptPackMarkdown = OpenApiSchema<"PromptPackMarkdown">;
export type StyleAnalysisJobLogs = OpenApiSchema<"StyleAnalysisJobLogsResponse">;
export type PlotAnalysisMeta = OpenApiSchema<"PlotAnalysisMeta">;
export type PlotAnalysisReportMarkdown = OpenApiSchema<"PlotAnalysisReportMarkdown">;
export type PlotSummaryMarkdown = OpenApiSchema<"PlotSummaryMarkdown">;
export type PlotPromptPackMarkdown = OpenApiSchema<"PlotPromptPackMarkdown">;
export type PlotAnalysisJobLogs = OpenApiSchema<"PlotAnalysisJobLogsResponse">;

export type StyleAnalysisJob = OpenApiSchema<"StyleAnalysisJobResponse">;
export type StyleAnalysisJobListItem = OpenApiSchema<"StyleAnalysisJobBaseResponse">;
export type StyleAnalysisJobStatus = StyleAnalysisJob["status"];
export type StyleAnalysisJobStage = NonNullable<StyleAnalysisJob["stage"]>;
export type StyleProfile = OpenApiSchema<"StyleProfileResponse">;
export type StyleProfileListItem = OpenApiSchema<"StyleProfileListItemResponse">;
export type PlotAnalysisJob = OpenApiSchema<"PlotAnalysisJobResponse">;
export type PlotAnalysisJobListItem = OpenApiSchema<"PlotAnalysisJobBaseResponse">;
export type PlotAnalysisJobStatus = PlotAnalysisJob["status"];
export type PlotAnalysisJobStage = NonNullable<PlotAnalysisJob["stage"]>;
export type PlotProfile = OpenApiSchema<"PlotProfileResponse">;
export type PlotProfileListItem = OpenApiSchema<"PlotProfileListItemResponse">;
export type SetupStatusResponse = OpenApiSchema<"SetupStatusResponse">;
export type SetupResponse = OpenApiSchema<"SetupResponse">;
export type StyleAnalysisJobStatusSnapshot = OpenApiSchema<"StyleAnalysisJobStatusResponse">;
export type PlotAnalysisJobStatusSnapshot = OpenApiSchema<"PlotAnalysisJobStatusResponse">;
export type StyleAnalysisJobCreatePayload =
  Omit<components["schemas"]["Body_create_style_analysis_job_api_v1_style_analysis_jobs_post"], "file"> & {
    file: File;
  };
export type PlotAnalysisJobCreatePayload =
  Omit<components["schemas"]["Body_create_plot_analysis_job_api_v1_plot_analysis_jobs_post"], "file"> & {
    file: File;
  };
export type BeatGenerateResponse = OpenApiSchema<"BeatGenerateResponse">;
export type BibleUpdateResponse = OpenApiSchema<"BibleUpdateResponse"> & {
  changed: boolean;
};
export type ConnectionTestResponse = OpenApiSchema<"ConnectionTestResponse">;

export type SetupPayload = components["schemas"]["SetupRequest"];
export type LoginPayload = components["schemas"]["LoginRequest"];
export type ProjectPayload = components["schemas"]["ProjectCreate"];
export type ProjectChapterUpdate = Partial<components["schemas"]["ProjectChapterUpdate"]> &
  Partial<ChapterMemorySyncSnapshot>;
export type ProviderPayload = components["schemas"]["ProviderConfigCreate"];

export type StyleProfileCreatePayload = components["schemas"]["StyleProfileCreate"];
export type StyleProfileUpdatePayload = components["schemas"]["StyleProfileUpdate"];
export type PlotProfileCreatePayload = components["schemas"]["PlotProfileCreate"];
export type PlotProfileUpdatePayload = components["schemas"]["PlotProfileUpdate"];

export type ConceptGeneratePayload = components["schemas"]["ConceptGenerateRequest"];
export type ConceptGenerateResult = components["schemas"]["ConceptGenerateResponse"];
export type ConceptItem = components["schemas"]["ConceptItem"];
