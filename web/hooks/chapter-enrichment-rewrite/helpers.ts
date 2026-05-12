import type {
  ChapterRewriteBatch,
  ChapterRewriteBatchItem,
  ProjectChapter,
} from "@/lib/types";
import type { ChapterRewriteItem, ChapterRewriteState } from "./types";

export const chapterRewriteBatchKeys = {
  list: (projectId: string) => ["chapter-rewrite-batches", projectId] as const,
  detail: (batchId: string | null) => ["chapter-rewrite-batch", batchId] as const,
};

export function sortChapters(chapters: ProjectChapter[]): ProjectChapter[] {
  return [...chapters].sort((left, right) =>
    left.volume_index - right.volume_index || left.chapter_index - right.chapter_index
  );
}

export function isBatchActive(batch: Pick<ChapterRewriteBatch, "status">) {
  return batch.status === "pending" || batch.status === "running";
}

export function isBatchReviewable(
  batch: Pick<ChapterRewriteBatch, "status" | "generated_count" | "applied_count">,
) {
  return batch.status !== "pending" && batch.status !== "running" && batch.generated_count > batch.applied_count;
}

export function isBatchActionable(
  batch: Pick<ChapterRewriteBatch, "status" | "generated_count" | "applied_count">,
) {
  return isBatchActive(batch) || isBatchReviewable(batch);
}

export function mapItemState(item: ChapterRewriteBatchItem): ChapterRewriteState {
  if (item.status === "waiting") return "waiting";
  if (item.status === "running") return "running";
  if (item.status === "generated") return "generated";
  if (item.status === "failed") return "failed";
  return "applied";
}

export function buildDisplayItem(
  item: ChapterRewriteBatchItem,
  chapter: ProjectChapter,
  preview: string,
  logs: string,
): ChapterRewriteItem {
  const state = mapItemState(item);
  return {
    id: item.id,
    chapter,
    state,
    jobId: item.child_run_id,
    preview,
    logs,
    statusLabel: item.stage ? `${item.status} / ${item.stage}` : item.status,
    errorMessage: item.error_message,
    applyErrorMessage: null,
  };
}

type BatchApplyCacheShape = {
  applied_count: number;
  total_count: number;
  items?: ChapterRewriteBatchItem[];
};

export function markBatchItemsApplied<T extends BatchApplyCacheShape>(batch: T, itemIds: Set<string>): T {
  if (!batch.items) {
    return {
      ...batch,
      applied_count: Math.min(batch.total_count, batch.applied_count + itemIds.size),
    };
  }
  const items = (batch.items ?? []).map((item) =>
    itemIds.has(item.id)
      ? { ...item, status: "applied" as const }
      : item,
  );
  return {
    ...batch,
    items,
    applied_count: items.filter((item) => item.status === "applied").length,
  } as T;
}

export function buildFallbackChapter(batch: ChapterRewriteBatch, item: ChapterRewriteBatchItem): ProjectChapter {
  return {
    id: item.chapter_id,
    project_id: batch.project_id,
    volume_index: 0,
    chapter_index: item.position,
    title: item.chapter_title ?? "未知章节",
    content: "",
    beats_markdown: "",
    summary: "",
    word_count: 0,
    memory_sync_status: null,
    memory_sync_source: null,
    memory_sync_scope: null,
    memory_sync_checked_at: null,
    memory_sync_checked_content_hash: null,
    memory_sync_error_message: null,
    memory_sync_proposed_characters_status: null,
    memory_sync_proposed_state: null,
    memory_sync_proposed_threads: null,
    memory_sync_proposed_summary: null,
    created_at: batch.created_at,
    updated_at: batch.updated_at,
  };
}
