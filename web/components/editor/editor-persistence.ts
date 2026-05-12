import { useCallback } from "react";

import { useUpdateProject, useUpdateProjectBible } from "@/hooks/use-project-query";
import { api } from "@/lib/api";
import type { ProjectBibleUpdate, ProjectChapter, ProjectChapterUpdate, ProjectUpdatePayload } from "@/lib/types";
import { queryKeys } from "@/hooks/use-chapters-query";
import { toast } from "sonner";
import type { QueryClient } from "@tanstack/react-query";
import type { StoreApi } from "zustand";

import type { EditorState } from "./editor-store";

type PersistOptions = {
  successMessage?: string;
  errorMessage?: string;
};

export function useEditorPersistence({
  projectId,
  queryClient,
  selectedChapterId,
  store,
}: {
  projectId: string;
  queryClient: QueryClient;
  selectedChapterId: string | null;
  store: StoreApi<EditorState>;
}) {
  const updateProjectMutation = useUpdateProject();
  const updateProjectBibleMutation = useUpdateProjectBible();

  const syncPersistedChapter = useCallback(
    (updatedChapter: ProjectChapter) => {
      queryClient.setQueryData(queryKeys.chapters(projectId), (prev: ProjectChapter[] | undefined) => {
        if (!prev) return [updatedChapter];
        return prev.map((chapter) =>
          chapter.id === updatedChapter.id ? { ...chapter, ...updatedChapter } : chapter,
        );
      });
      if (selectedChapterId === updatedChapter.id) {
        store.getState().setSavedChapterContent(updatedChapter.content);
      }
      return updatedChapter;
    },
    [projectId, queryClient, selectedChapterId, store],
  );

  const persistChapterUpdate = useCallback(
    async (chapterId: string, payload: ProjectChapterUpdate) => {
      const updated = await api.updateProjectChapter(projectId, chapterId, payload);
      return syncPersistedChapter(updated);
    },
    [projectId, syncPersistedChapter],
  );

  const persistProjectUpdate = useCallback(
    async (payload: Partial<ProjectUpdatePayload>, options: PersistOptions = {}) => {
      try {
        await updateProjectMutation.mutateAsync({ id: projectId, payload });
        if (options.successMessage) toast.success(options.successMessage);
      } catch {
        if (options.errorMessage) toast.error(options.errorMessage);
      }
    },
    [projectId, updateProjectMutation],
  );

  const persistProjectBibleUpdate = useCallback(
    async (payload: Partial<ProjectBibleUpdate>, options: PersistOptions = {}) => {
      try {
        await updateProjectBibleMutation.mutateAsync({ id: projectId, payload });
        if (options.successMessage) toast.success(options.successMessage);
      } catch {
        if (options.errorMessage) toast.error(options.errorMessage);
      }
    },
    [projectId, updateProjectBibleMutation],
  );

  const persistProjectField = useCallback(
    async (field: string, value: string) => {
      if (field === "description") {
        await persistProjectUpdate({ [field]: value }, { errorMessage: "保存失败" });
      } else {
        await persistProjectBibleUpdate({ [field]: value }, { errorMessage: "保存失败" });
      }
    },
    [persistProjectUpdate, persistProjectBibleUpdate],
  );

  return {
    syncPersistedChapter,
    persistChapterUpdate,
    persistProjectUpdate,
    persistProjectBibleUpdate,
    persistProjectField,
  };
}
