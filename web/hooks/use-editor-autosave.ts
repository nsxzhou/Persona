import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import type { ProjectChapter } from "@/lib/types";
import { useEditorStore } from "@/components/editor/editor-store";

type PendingSave = { chapterId: string; content: string };

export function useEditorAutosave(
  projectId: string,
  chapterId: string | null,
  disabled: boolean,
  onSaved?: (chapter: ProjectChapter) => void,
) {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaveError, setLastSaveError] = useState<Error | null>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingRef = useRef<PendingSave | null>(null);
  const onSavedRef = useRef(onSaved);

  useEffect(() => {
    onSavedRef.current = onSaved;
  }, [onSaved]);

  const persistContent = useCallback(
    async (targetChapterId: string, nextContent: string, errorMessage: string) => {
      setIsSaving(true);
      try {
        const updated = await api.updateProjectChapter(projectId, targetChapterId, {
          content: nextContent,
        });
        setLastSaveError(null);
        onSavedRef.current?.(updated);
        return updated;
      } catch (e) {
        setLastSaveError(e instanceof Error ? e : new Error(String(e)));
        console.error("Failed to save content", e);
        toast.error(errorMessage);
        throw e;
      } finally {
        setIsSaving(false);
      }
    },
    [projectId],
  );

  const clearPendingTimer = useCallback(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }
  }, []);

  const flushPendingSave = useCallback(async () => {
    clearPendingTimer();
    const pending = pendingRef.current;
    pendingRef.current = null;
    if (!pending) return null;
    return await persistContent(pending.chapterId, pending.content, "自动保存失败");
  }, [clearPendingTimer, persistContent]);

  const saveNow = useCallback(
    async (nextContent: string) => {
      if (!chapterId) {
        throw new Error("未选择章节");
      }
      clearPendingTimer();
      pendingRef.current = null;
      return persistContent(chapterId, nextContent, "保存失败");
    },
    [chapterId, clearPendingTimer, persistContent],
  );

  useEffect(() => {
    return useEditorStore.subscribe((state) => {
      const currentContent = state.content;
      const savedContent = state.savedChapterContent;

      if (disabled || !chapterId || currentContent === savedContent) {
        return;
      }

      pendingRef.current = { chapterId, content: currentContent };
      clearPendingTimer();

      saveTimeoutRef.current = setTimeout(() => {
        saveTimeoutRef.current = null;
        const pending = pendingRef.current;
        pendingRef.current = null;
        if (!pending) return;
        void persistContent(pending.chapterId, pending.content, "自动保存失败").catch(() => {});
      }, 1000);
    });
  }, [chapterId, disabled, clearPendingTimer, persistContent]);

  useEffect(() => {
    return () => {
      const pending = pendingRef.current;
      if (!pending) return;
      pendingRef.current = null;
      void persistContent(pending.chapterId, pending.content, "自动保存失败").catch(() => {});
    };
  }, [chapterId, persistContent]);

  return {
    isSaving,
    saveNow,
    flushPendingSave,
    lastSaveError,
    clearSaveError: () => setLastSaveError(null),
  };
}
