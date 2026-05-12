import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";

import { WorkflowRunsPageView } from "@/components/workflow-runs-page-view";
import { getServerApi } from "@/lib/server-api";
import { projectsQueryKeys } from "@/lib/projects-query-keys";
import {
  WORKFLOW_RUNS_ALL_FILTER,
  WORKFLOW_RUNS_PAGE_SIZE,
  workflowRunsQueryKeys,
} from "@/lib/workflow-runs-query-keys";

export default async function WorkflowRunsPage() {
  const api = await getServerApi();
  const queryClient = new QueryClient();

  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: workflowRunsQueryKeys.list(
        WORKFLOW_RUNS_ALL_FILTER,
        WORKFLOW_RUNS_ALL_FILTER,
        WORKFLOW_RUNS_ALL_FILTER,
        1,
      ),
      queryFn: () =>
        api.listNovelWorkflows({
          projectId: null,
          intentType: null,
          status: null,
          offset: 0,
          limit: WORKFLOW_RUNS_PAGE_SIZE,
        }),
    }),
    queryClient.prefetchQuery({
      queryKey: projectsQueryKeys.workflowFilter(),
      queryFn: () => api.getProjects({ includeArchived: true, offset: 0, limit: 100 }),
    }),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <WorkflowRunsPageView />
    </HydrationBoundary>
  );
}
