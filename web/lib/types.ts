import type { components } from "@/lib/api/generated/openapi";

type OpenApiSchema<Name extends keyof components["schemas"]> = components["schemas"][Name];

export type User = OpenApiSchema<"UserResponse">;
export type ProviderConfig = OpenApiSchema<"ProviderConfigResponse">;
export type Project = OpenApiSchema<"ProjectResponse">;
export type ProjectSummary = OpenApiSchema<"ProjectSummaryResponse">;
export type ProjectBible = OpenApiSchema<"ProjectBibleResponse">;
export type ProjectBibleUpdate = OpenApiSchema<"ProjectBibleUpdate">;
export type MemorySyncStatus = NonNullable<ProjectChapter["memory_sync_status"]>;
export type MemorySyncSource = NonNullable<ProjectChapter["memory_sync_source"]>;
export type MemorySyncScope = NonNullable<ProjectChapter["memory_sync_scope"]>;

export type ProjectChapter = OpenApiSchema<"ProjectChapterResponse">;

export type AnalysisMeta = OpenApiSchema<"AnalysisMeta">;
export type AnalysisReportMarkdown = OpenApiSchema<"AnalysisReportMarkdown">;
export type VoiceProfile = OpenApiSchema<"VoiceProfile">;
export type VoiceProfileMarkdown = OpenApiSchema<"VoiceProfileMarkdown">;
export type StyleAnalysisJobLogs = OpenApiSchema<"StyleAnalysisJobLogsResponse">;
export type PlotAnalysisMeta = OpenApiSchema<"PlotAnalysisMeta">;
export type PlotAnalysisReportMarkdown = OpenApiSchema<"PlotAnalysisReportMarkdown">;
export type PlotWritingGuideProfile = OpenApiSchema<"PlotWritingGuideProfile">;
export type StoryEngineMarkdown = OpenApiSchema<"StoryEngineMarkdown">;
export type PlotSkeletonMarkdown = OpenApiSchema<"PlotSkeletonMarkdown">;
export type PlotAnalysisJobLogs = OpenApiSchema<"PlotAnalysisJobLogsResponse">;
export type TargetMarket = "mainstream" | "nsfw";
export type GenreMother =
  | "xianxia"
  | "urban"
  | "historical_power"
  | "infinite_flow"
  | "gaming";
export type GenerationProfile = OpenApiSchema<"GenerationProfile">;

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
export type BibleUpdateResponse = OpenApiSchema<"BibleUpdateResponse">;
export type ConnectionTestResponse = OpenApiSchema<"ConnectionTestResponse">;

export type SetupPayload = components["schemas"]["SetupRequest"];
export type LoginPayload = components["schemas"]["LoginRequest"];
export type ProjectPayload = components["schemas"]["ProjectCreate"];
export type ProjectChapterUpdate = components["schemas"]["ProjectChapterUpdate"];
export type ProviderPayload = components["schemas"]["ProviderConfigCreate"];

export type StyleProfileCreatePayload = components["schemas"]["StyleProfileCreate"];
export type StyleProfileUpdatePayload = components["schemas"]["StyleProfileUpdate"];
export type PlotProfileCreatePayload = components["schemas"]["PlotProfileCreate"];
export type PlotProfileUpdatePayload = components["schemas"]["PlotProfileUpdate"];

export type ConceptGeneratePayload = components["schemas"]["ConceptGenerateRequest"];
export type ConceptGenerateResult = components["schemas"]["ConceptGenerateResponse"];
export type ConceptItem = components["schemas"]["ConceptItem"];
