import type { Requester } from "@/lib/api/requester";
import { createNovelWorkflowClient } from "@/lib/novel-workflow-client";
import type {
  NovelWorkflow,
  NovelWorkflowCreatePayload,
  NovelWorkflowDecisionPayload,
  NovelWorkflowListItem,
  NovelWorkflowLogs,
  NovelWorkflowStatusSnapshot,
} from "@/lib/types";

export function createNovelWorkflowApiClient(request: Requester) {
  const workflowClient = createNovelWorkflowClient(request);

  return {
    listNovelWorkflows: (params?: {
      projectId?: string | null;
      intentType?: NovelWorkflowCreatePayload["intent_type"] | null;
      status?: NovelWorkflowListItem["status"] | null;
      offset?: number;
      limit?: number;
    }) => {
      const query = new URLSearchParams();
      if (params?.projectId) query.set("project_id", params.projectId);
      if (params?.intentType) query.set("intent_type", params.intentType);
      if (params?.status) query.set("status", params.status);
      query.set("offset", String(params?.offset ?? 0));
      query.set("limit", String(params?.limit ?? 50));
      return request<NovelWorkflowListItem[]>(`/api/v1/novel-workflows?${query.toString()}`);
    },
    createNovelWorkflow: (payload: NovelWorkflowCreatePayload) =>
      request<NovelWorkflowListItem>("/api/v1/novel-workflows", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    clearNovelWorkflowHistory: () =>
      request<void>("/api/v1/novel-workflows", {
        method: "DELETE",
      }),
    getNovelWorkflowStatus: (id: string) =>
      request<NovelWorkflowStatusSnapshot>(`/api/v1/novel-workflows/${id}/status`),
    getNovelWorkflow: (id: string) =>
      request<NovelWorkflow>(`/api/v1/novel-workflows/${id}`),
    getNovelWorkflowLogs: (id: string, offset = 0) =>
      request<NovelWorkflowLogs>(`/api/v1/novel-workflows/${id}/logs?offset=${offset}`),
    getNovelWorkflowArtifact: (id: string, artifactName: string) =>
      request<string>(`/api/v1/novel-workflows/${id}/artifacts/${artifactName}`),
    pauseNovelWorkflow: (id: string) =>
      request<NovelWorkflowStatusSnapshot>(`/api/v1/novel-workflows/${id}/pause`, {
        method: "POST",
      }),
    resumeNovelWorkflow: (id: string) =>
      request<NovelWorkflowStatusSnapshot>(`/api/v1/novel-workflows/${id}/resume`, {
        method: "POST",
      }),
    decideNovelWorkflow: (id: string, payload: NovelWorkflowDecisionPayload) =>
      request<NovelWorkflowStatusSnapshot>(`/api/v1/novel-workflows/${id}/decision`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    waitForNovelWorkflow: workflowClient.waitForNovelWorkflow,
    generateConcepts: workflowClient.generateConcepts,
    runSelectionRewriteWorkflow: workflowClient.runSelectionRewriteWorkflow,
    proposeBibleUpdate: workflowClient.proposeBibleUpdate,
    runBeatsWorkflow: workflowClient.runBeatsWorkflow,
    runBeatExpandWorkflow: workflowClient.runBeatExpandWorkflow,
    runChapterExpandWorkflow: workflowClient.runChapterExpandWorkflow,
    runSectionWorkflow: workflowClient.runSectionWorkflow,
    streamNovelWorkflowArtifact: workflowClient.streamNovelWorkflowArtifact,
    runVolumeWorkflow: workflowClient.runVolumeWorkflow,
    runVolumeChaptersWorkflow: workflowClient.runVolumeChaptersWorkflow,
  };
}
