import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import type { Project, ProjectPayload } from "@/lib/types";

const MIN_LENGTH_FOR_BIBLE_UPDATE = 200;

export type RuntimeUpdateDiffState = {
  open: boolean;
  currentState: string;
  proposedState: string;
  currentThreads: string;
  proposedThreads: string;
};

const EMPTY_DIFF_STATE: RuntimeUpdateDiffState = {
  open: false,
  currentState: "",
  proposedState: "",
  currentThreads: "",
  proposedThreads: "",
};

export function useRuntimeUpdateProposal({
  projectId,
  project,
  persistProjectUpdate,
}: {
  projectId: string;
  project: Pick<Project, "runtime_state" | "runtime_threads">;
  persistProjectUpdate: (
    payload: Partial<ProjectPayload>,
    options?: { successMessage?: string; errorMessage?: string },
  ) => Promise<unknown>;
}) {
  const [bibleDiff, setBibleDiff] = useState<RuntimeUpdateDiffState>(EMPTY_DIFF_STATE);

  const dismissRuntimeUpdate = useCallback(() => {
    setBibleDiff(EMPTY_DIFF_STATE);
  }, []);

  const proposeRuntimeUpdate = useCallback(
    async (generated: string) => {
      if (generated.trim().length < MIN_LENGTH_FOR_BIBLE_UPDATE) return;

      try {
        const { proposed_runtime_state, proposed_runtime_threads } = await api.proposeBibleUpdate(
          projectId,
          project.runtime_state,
          project.runtime_threads ?? "",
          generated,
        );
        const stateChanged =
          proposed_runtime_state && proposed_runtime_state !== project.runtime_state;
        const threadsChanged =
          proposed_runtime_threads &&
          proposed_runtime_threads !== (project.runtime_threads ?? "");

        if (stateChanged || threadsChanged) {
          setBibleDiff({
            open: true,
            currentState: project.runtime_state,
            proposedState: proposed_runtime_state,
            currentThreads: project.runtime_threads ?? "",
            proposedThreads: proposed_runtime_threads,
          });
        }
      } catch {
        // Runtime proposals should never block prose generation.
      }
    },
    [project.runtime_state, project.runtime_threads, projectId],
  );

  const acceptRuntimeUpdate = useCallback(
    async (state: string, threads: string) => {
      await persistProjectUpdate(
        { runtime_state: state, runtime_threads: threads },
        {
          successMessage: "运行时状态已更新",
          errorMessage: "更新运行时状态失败",
        },
      );
      dismissRuntimeUpdate();
    },
    [dismissRuntimeUpdate, persistProjectUpdate],
  );

  return {
    bibleDiff,
    proposeRuntimeUpdate,
    acceptRuntimeUpdate,
    dismissRuntimeUpdate,
  };
}
