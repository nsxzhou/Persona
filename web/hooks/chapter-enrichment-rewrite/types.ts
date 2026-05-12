import type { ProjectChapter } from "@/lib/types";

export type ChapterRewriteState =
  | "waiting"
  | "running"
  | "generated"
  | "failed"
  | "applying"
  | "applied"
  | "apply_failed";

export type ChapterRewriteItem = {
  id: string;
  chapter: ProjectChapter;
  state: ChapterRewriteState;
  jobId: string | null;
  preview: string;
  logs: string;
  statusLabel: string;
  errorMessage: string | null;
  applyErrorMessage: string | null;
};
