import type { components } from "@/lib/api/generated/openapi";

type OpenApiSchema<Name extends keyof components["schemas"]> = components["schemas"][Name];

export type User = OpenApiSchema<"UserResponse">;
export type ProviderConfig = OpenApiSchema<"ProviderConfigResponse">;
export type ProviderSummary = OpenApiSchema<"ProviderSummary">;
export type Project = OpenApiSchema<"ProjectResponse">;

export type AnalysisMeta = OpenApiSchema<"AnalysisMeta">;
export type AnalysisReportMarkdown = OpenApiSchema<"AnalysisReportMarkdown">;
export type StyleSummaryMarkdown = OpenApiSchema<"StyleSummaryMarkdown">;
export type PromptPackMarkdown = OpenApiSchema<"PromptPackMarkdown">;
export type StyleAnalysisJobLogs = OpenApiSchema<"StyleAnalysisJobLogsResponse">;
export type StyleSampleFile = OpenApiSchema<"StyleSampleFileResponse">;

export type StyleAnalysisJob = OpenApiSchema<"StyleAnalysisJobResponse">;
export type StyleAnalysisJobListItem = OpenApiSchema<"StyleAnalysisJobListItemResponse">;
export type StyleAnalysisJobStatus = StyleAnalysisJob["status"];
export type StyleAnalysisJobStage = NonNullable<StyleAnalysisJob["stage"]>;
export type StyleProfile = OpenApiSchema<"StyleProfileResponse">;
export type StyleProfileListItem = OpenApiSchema<"StyleProfileListItemResponse">;

export type SetupPayload = components["schemas"]["SetupRequest"];
export type LoginPayload = components["schemas"]["LoginRequest"];
export type ProjectPayload = components["schemas"]["ProjectCreate"];
export type ProviderPayload = components["schemas"]["ProviderConfigCreate"];
export type ProviderUpdatePayload = components["schemas"]["ProviderConfigUpdate"];

export type StyleProfileCreatePayload = components["schemas"]["StyleProfileCreate"];
export type StyleProfileUpdatePayload = components["schemas"]["StyleProfileUpdate"];
