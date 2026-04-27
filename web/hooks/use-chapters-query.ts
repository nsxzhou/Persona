import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ProjectChapter } from "@/lib/types";

export const queryKeys = {
  chapters: (projectId: string) => ["projects", projectId, "chapters"] as const,
};

export function useChaptersQuery(projectId: string, initialData?: ProjectChapter[]) {
  return useQuery({
    queryKey: queryKeys.chapters(projectId),
    queryFn: () => api.getProjectChapters(projectId),
    initialData,
  });
}

export function useSyncChapters() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => api.syncProjectChapters(projectId),
    onSuccess: (data, projectId) => {
      queryClient.setQueryData(queryKeys.chapters(projectId), data);
    },
  });
}
