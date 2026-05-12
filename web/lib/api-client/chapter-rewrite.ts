import type { Requester } from "@/lib/api/requester";
import type {
  ChapterRewriteBatch,
  ChapterRewriteBatchApplyItemResponse,
  ChapterRewriteBatchApplyResponse,
  ChapterRewriteBatchCreatePayload,
  ChapterRewriteBatchListItem,
  ChapterRewriteBatchLogs,
  NovelChapterRewriteJob,
  NovelChapterRewriteJobApplyResponse,
  NovelChapterRewriteJobCreatePayload,
  NovelChapterRewriteJobLogs,
  NovelChapterRewriteJobStatus,
} from "@/lib/types";

export function createChapterRewriteApiClient(request: Requester) {
  return {
    createNovelChapterRewriteJob: (payload: NovelChapterRewriteJobCreatePayload) =>
      request<NovelChapterRewriteJob>("/api/v1/novel-chapter-rewrite-jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getNovelChapterRewriteJobStatus: (id: string) =>
      request<NovelChapterRewriteJobStatus>(`/api/v1/novel-chapter-rewrite-jobs/${id}/status`),
    getNovelChapterRewriteJobLogs: (id: string, offset = 0) =>
      request<NovelChapterRewriteJobLogs>(
        `/api/v1/novel-chapter-rewrite-jobs/${id}/logs?offset=${offset}`,
      ),
    getNovelChapterRewriteJobArtifact: (id: string) =>
      request<string>(`/api/v1/novel-chapter-rewrite-jobs/${id}/artifact`),
    applyNovelChapterRewriteJob: (id: string) =>
      request<NovelChapterRewriteJobApplyResponse>(
        `/api/v1/novel-chapter-rewrite-jobs/${id}/apply`,
        {
          method: "POST",
        },
      ),
    createChapterRewriteBatch: (payload: ChapterRewriteBatchCreatePayload) =>
      request<ChapterRewriteBatch>("/api/v1/chapter-rewrite-batches", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getChapterRewriteBatches: (params?: {
      projectId?: string | null;
      offset?: number;
      limit?: number;
    }) => {
      const query = new URLSearchParams();
      if (params?.projectId) query.set("project_id", params.projectId);
      query.set("offset", String(params?.offset ?? 0));
      query.set("limit", String(params?.limit ?? 50));
      return request<ChapterRewriteBatchListItem[]>(
        `/api/v1/chapter-rewrite-batches?${query.toString()}`,
      );
    },
    getChapterRewriteBatch: (id: string) =>
      request<ChapterRewriteBatch>(`/api/v1/chapter-rewrite-batches/${id}`),
    getChapterRewriteBatchItemLogs: (batchId: string, itemId: string, offset = 0) =>
      request<ChapterRewriteBatchLogs>(
        `/api/v1/chapter-rewrite-batches/${batchId}/items/${itemId}/logs?offset=${offset}`,
      ),
    getChapterRewriteBatchItemArtifact: (batchId: string, itemId: string) =>
      request<string>(`/api/v1/chapter-rewrite-batches/${batchId}/items/${itemId}/artifact`),
    applyChapterRewriteBatchItem: (batchId: string, itemId: string) =>
      request<ChapterRewriteBatchApplyItemResponse>(
        `/api/v1/chapter-rewrite-batches/${batchId}/items/${itemId}/apply`,
        { method: "POST" },
      ),
    applyChapterRewriteBatch: (batchId: string) =>
      request<ChapterRewriteBatchApplyResponse>(
        `/api/v1/chapter-rewrite-batches/${batchId}/apply`,
        { method: "POST" },
      ),
  };
}
