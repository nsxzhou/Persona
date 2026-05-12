import type { Requester } from "@/lib/api/requester";
import { createAnalysisApiClient } from "@/lib/api-client/analysis";
import { createAuthApiClient } from "@/lib/api-client/auth";
import { createChapterRewriteApiClient } from "@/lib/api-client/chapter-rewrite";
import { createNovelImportApiClient } from "@/lib/api-client/novel-imports";
import { createNovelWorkflowApiClient } from "@/lib/api-client/novel-workflows";
import { createProviderApiClient } from "@/lib/api-client/providers";
import { createProjectApiClient } from "@/lib/api-client/projects";

export type {
  RegenerateOptions,
  SelectionRewriteWorkflowPayload,
} from "@/lib/novel-workflow-client";

export function createApiClient(request: Requester) {
  return {
    ...createAuthApiClient(request),
    ...createProviderApiClient(request),
    ...createProjectApiClient(request),
    ...createNovelImportApiClient(request),
    ...createChapterRewriteApiClient(request),
    ...createNovelWorkflowApiClient(request),
    ...createAnalysisApiClient(request),
  };
}
