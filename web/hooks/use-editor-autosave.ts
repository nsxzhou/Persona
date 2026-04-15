import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";

export function useEditorAutosave(
  projectId: string,
  currentContent: string,
  savedContent: string,
  disabled: boolean
) {
  const [isSaving, setIsSaving] = useState(false);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (disabled || currentContent === savedContent) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      setIsSaving(true);
      try {
        await api.updateProject(projectId, { content: currentContent });
      } catch (e) {
        console.error("Failed to save content", e);
        toast.error("自动保存失败");
      } finally {
        setIsSaving(false);
      }
    }, 1000);

    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    };
  }, [currentContent, savedContent, projectId, disabled]);

  return { isSaving };
}
