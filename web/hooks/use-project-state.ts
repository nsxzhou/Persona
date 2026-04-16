import { useCallback, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Project, ProjectPayload } from "@/lib/types";

type PersistProjectUpdateOptions = {
  successMessage?: string;
  errorMessage?: string;
};

export function useProjectState(initialProject: Project) {
  const [projectData, setProjectData] = useState(initialProject);

  const persistProjectUpdate = useCallback(
    async (
      payload: Partial<ProjectPayload>,
      options: PersistProjectUpdateOptions = {},
    ) => {
      try {
        const updated = await api.updateProject(projectData.id, payload);
        setProjectData((prev) => ({ ...prev, ...updated }));
        if (options.successMessage) {
          toast.success(options.successMessage);
        }
        return updated;
      } catch (error) {
        if (options.errorMessage) {
          toast.error(options.errorMessage);
        }
        throw error;
      }
    },
    [projectData.id],
  );

  return {
    projectData,
    setProjectData,
    persistProjectUpdate,
  };
}
