import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import {
  chapterRewriteBatchKeys,
  isBatchActionable,
  isBatchActive,
} from "./helpers";

const POLL_INTERVAL_MS = 1000;

export function useChapterRewriteBatchQueries({
  projectId,
  activeBatchId,
  setActiveBatchId,
}: {
  projectId: string;
  activeBatchId: string | null;
  setActiveBatchId: (batchId: string | null) => void;
}) {
  const listQuery = useQuery({
    queryKey: chapterRewriteBatchKeys.list(projectId),
    queryFn: () => api.getChapterRewriteBatches({ projectId }),
    refetchInterval: (query) =>
      query.state.data?.some((batch) => isBatchActive(batch)) ? POLL_INTERVAL_MS : false,
  });

  useEffect(() => {
    if (activeBatchId || !listQuery.data?.length) return;
    const candidate = listQuery.data.find(isBatchActionable);
    if (candidate) {
      setActiveBatchId(candidate.id);
    }
  }, [activeBatchId, listQuery.data, setActiveBatchId]);

  const detailQuery = useQuery({
    queryKey: chapterRewriteBatchKeys.detail(activeBatchId),
    queryFn: () => api.getChapterRewriteBatch(activeBatchId!),
    enabled: Boolean(activeBatchId),
    refetchInterval: (query) =>
      query.state.data && isBatchActive(query.state.data) ? POLL_INTERVAL_MS : false,
  });

  const batch = detailQuery.data ?? null;
  const batchItems = useMemo(() => batch?.items ?? [], [batch?.items]);

  return { listQuery, detailQuery, batch, batchItems };
}
