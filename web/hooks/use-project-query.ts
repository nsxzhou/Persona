import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Project, ProjectBible, ProjectBibleUpdate, ProjectUpdatePayload } from "@/lib/types";
import { toast } from "sonner";

export const projectKeys = {
  all: ["projects"] as const,
  detail: (id: string) => [...projectKeys.all, id] as const,
  bible: (id: string) => [...projectKeys.detail(id), "bible"] as const,
};

export function useProjectQuery(projectId: string, initialData?: Project) {
  return useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => api.getProject(projectId),
    initialData,
  });
}

export function useProjectBibleQuery(projectId: string, initialData?: ProjectBible) {
  return useQuery({
    queryKey: projectKeys.bible(projectId),
    queryFn: () => api.getProjectBible(projectId),
    initialData,
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ProjectUpdatePayload> }) =>
      api.updateProject(id, payload),
    onMutate: async ({ id, payload }) => {
      await queryClient.cancelQueries({ queryKey: projectKeys.detail(id) });
      const previousProject = queryClient.getQueryData<Project>(projectKeys.detail(id));

      if (previousProject) {
        queryClient.setQueryData(projectKeys.detail(id), {
          ...previousProject,
          ...payload,
        });
      }

      return { previousProject };
    },
    onError: (err, variables, context) => {
      if (context?.previousProject) {
        queryClient.setQueryData(projectKeys.detail(variables.id), context.previousProject);
      }
      toast.error("Failed to update project");
    },
    onSettled: (data, error, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(variables.id) });
    },
  });
}

export function useUpdateProjectBible() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ProjectBibleUpdate> }) =>
      api.updateProjectBible(id, payload),
    onMutate: async ({ id, payload }) => {
      await queryClient.cancelQueries({ queryKey: projectKeys.bible(id) });
      const previousBible = queryClient.getQueryData<ProjectBible>(projectKeys.bible(id));

      if (previousBible) {
        queryClient.setQueryData<ProjectBible>(projectKeys.bible(id), {
          ...previousBible,
          ...payload,
        } as ProjectBible);
      }

      return { previousBible };
    },
    onError: (err, variables, context) => {
      if (context?.previousBible) {
        queryClient.setQueryData(projectKeys.bible(variables.id), context.previousBible);
      }
      toast.error("Failed to update project bible");
    },
    onSettled: (data, error, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.bible(variables.id) });
    },
  });
}
