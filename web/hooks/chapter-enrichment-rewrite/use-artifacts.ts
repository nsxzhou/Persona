import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { ChapterRewriteBatch, ChapterRewriteBatchItem } from "@/lib/types";

export function useChapterRewriteArtifacts({
  batch,
  batchItems,
  activeItemId,
}: {
  batch: ChapterRewriteBatch | null;
  batchItems: ChapterRewriteBatchItem[];
  activeItemId: string | null;
}) {
  const [previews, setPreviews] = useState<Record<string, string>>({});
  const [logsByItemId, setLogsByItemId] = useState<Record<string, string>>({});
  const requestedPreviewIdsRef = useRef<Set<string>>(new Set());

  const clearArtifacts = useCallback(() => {
    setPreviews({});
    requestedPreviewIdsRef.current.clear();
    setLogsByItemId({});
  }, []);

  useEffect(() => {
    if (!batch) return;
    let cancelled = false;
    const currentItemIds = new Set(batchItems.map((item) => item.id));
    requestedPreviewIdsRef.current = new Set(
      [...requestedPreviewIdsRef.current].filter((itemId) => currentItemIds.has(itemId)),
    );
    for (const item of batchItems) {
      if (
        (item.status === "generated" || item.status === "applied") &&
        !requestedPreviewIdsRef.current.has(item.id)
      ) {
        requestedPreviewIdsRef.current.add(item.id);
        api.getChapterRewriteBatchItemArtifact(batch.id, item.id)
          .then((artifact) => {
            if (cancelled) return;
            setPreviews((current) => ({ ...current, [item.id]: artifact }));
          })
          .catch(() => {
            if (cancelled) return;
            setPreviews((current) => ({ ...current, [item.id]: "" }));
          });
      }
    }
    return () => {
      cancelled = true;
    };
  }, [batch, batchItems]);

  useEffect(() => {
    if (!batch || !activeItemId) return;
    const item = batchItems.find((candidate) => candidate.id === activeItemId);
    if (!item?.child_run_id) return;
    api.getChapterRewriteBatchItemLogs(batch.id, activeItemId)
      .then((result) => {
        setLogsByItemId((current) => ({ ...current, [activeItemId]: result.content }));
      })
      .catch(() => undefined);
  }, [activeItemId, batch, batchItems]);

  return { previews, logsByItemId, clearArtifacts };
}
