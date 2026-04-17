import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import type { ProjectChapter } from "@/lib/types";

type PendingSave = { chapterId: string; content: string };

export function useEditorAutosave(
  projectId: string,
  chapterId: string | null,
  currentContent: string,
  savedContent: string,
  disabled: boolean,
  onSaved?: (chapter: ProjectChapter) => void,
) {
  const [isSaving, setIsSaving] = useState(false);
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
        onSavedRef.current?.(updated);
        return updated;
      } catch (e) {
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
    try {
      return await persistContent(pending.chapterId, pending.content, "自动保存失败");
    } catch {
      return null;
    }
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
      void persistContent(pending.chapterId, pending.content, "自动保存失败").catch(() => {
        // toast already raised in persistContent
      });
    }, 1000);

    return clearPendingTimer;
  }, [chapterId, currentContent, savedContent, disabled, clearPendingTimer, persistContent]);

  // Flush pending save whenever the active chapter changes or the hook unmounts,
  // so unsaved edits are not lost when switching chapters within the debounce window.
  useEffect(() => {
    return () => {
      const pending = pendingRef.current;
      if (!pending) return;
      pendingRef.current = null;
      void persistContent(pending.chapterId, pending.content, "自动保存失败").catch(() => {});
    };
  }, [chapterId, persistContent]);

  return { isSaving, saveNow, flushPendingSave };
}
