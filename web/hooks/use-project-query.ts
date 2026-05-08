import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Project,
  ProjectBible,
  ProjectBibleUpdate,
  ProjectPromptAsset,
  ProjectPromptAssetApplySuggestionsRequest,
  ProjectPromptAssetCreate,
  ProjectPromptAssetUpdate,
  PromptStackPreviewRequest,
  ProjectUpdatePayload,
} from "@/lib/types";
import { toast } from "sonner";

export const projectKeys = {
  all: ["projects"] as const,
  detail: (id: string) => [...projectKeys.all, id] as const,
  bible: (id: string) => [...projectKeys.detail(id), "bible"] as const,
  promptAssets: (id: string) => [...projectKeys.detail(id), "prompt-assets"] as const,
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

export function useProjectPromptAssetsQuery(projectId: string) {
  return useQuery({
    queryKey: projectKeys.promptAssets(projectId),
    queryFn: () => api.getProjectPromptAssets(projectId),
  });
}

export function useCreateProjectPromptAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, payload }: { projectId: string; payload: ProjectPromptAssetCreate }) =>
      api.createProjectPromptAsset(projectId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.promptAssets(variables.projectId) });
    },
    onError: () => {
      toast.error("Failed to create prompt asset");
    },
  });
}

export function useUpdateProjectPromptAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      assetId,
      payload,
    }: {
      projectId: string;
      assetId: string;
      payload: ProjectPromptAssetUpdate;
    }) => api.updateProjectPromptAsset(projectId, assetId, payload),
    onMutate: async ({ projectId, assetId, payload }) => {
      await queryClient.cancelQueries({ queryKey: projectKeys.promptAssets(projectId) });
      const previousAssets = queryClient.getQueryData<ProjectPromptAsset[]>(
        projectKeys.promptAssets(projectId),
      );
      if (previousAssets) {
        queryClient.setQueryData<ProjectPromptAsset[]>(
          projectKeys.promptAssets(projectId),
          previousAssets.map((asset) => (
            asset.id === assetId ? { ...asset, ...payload } as ProjectPromptAsset : asset
          )),
        );
      }
      return { previousAssets };
    },
    onError: (_err, variables, context) => {
      if (context?.previousAssets) {
        queryClient.setQueryData(projectKeys.promptAssets(variables.projectId), context.previousAssets);
      }
      toast.error("Failed to update prompt asset");
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.promptAssets(variables.projectId) });
    },
  });
}

export function useDeleteProjectPromptAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, assetId }: { projectId: string; assetId: string }) =>
      api.deleteProjectPromptAsset(projectId, assetId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.promptAssets(variables.projectId) });
    },
    onError: () => {
      toast.error("Failed to delete prompt asset");
    },
  });
}

export function useApplyProjectPromptAssetSuggestions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      payload,
    }: {
      projectId: string;
      payload: ProjectPromptAssetApplySuggestionsRequest;
    }) => api.applyProjectPromptAssetSuggestions(projectId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.promptAssets(variables.projectId) });
    },
    onError: () => {
      toast.error("Failed to apply prompt asset suggestions");
    },
  });
}

export function usePreviewProjectPromptStack() {
  return useMutation({
    mutationFn: ({ projectId, payload }: { projectId: string; payload: PromptStackPreviewRequest }) =>
      api.previewProjectPromptStack(projectId, payload),
    onError: () => {
      toast.error("Failed to preview prompt stack");
    },
  });
}
