import type { NovelWorkflowCreatePayload, NovelWorkflowListItem } from "@/lib/types";

export const WORKFLOW_RUNS_PAGE_SIZE = 20;
export const WORKFLOW_RUNS_ALL_FILTER = "__all__";

export type WorkflowRunsIntentFilter =
  | NovelWorkflowCreatePayload["intent_type"]
  | typeof WORKFLOW_RUNS_ALL_FILTER;
export type WorkflowRunsStatusFilter =
  | NovelWorkflowListItem["status"]
  | typeof WORKFLOW_RUNS_ALL_FILTER;

export const workflowRunsQueryKeys = {
  all: ["novel-workflows"] as const,
  list: (
    projectId: string,
    intentType: WorkflowRunsIntentFilter,
    status: WorkflowRunsStatusFilter,
    page: number,
  ) => [...workflowRunsQueryKeys.all, projectId, intentType, status, page] as const,
} as const;
