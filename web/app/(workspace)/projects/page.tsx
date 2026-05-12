import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";

import { ProjectsPageClient } from "@/components/projects-page-view";
import { PROJECTS_PAGE_SIZE, projectsQueryKeys } from "@/lib/projects-query-keys";
import { getServerApi } from "@/lib/server-api";

export default async function ProjectsPage() {
  const api = await getServerApi();
  const queryClient = new QueryClient();

  await queryClient.prefetchQuery({
    queryKey: projectsQueryKeys.list(false, 1),
    queryFn: () =>
      api.getProjects({
        includeArchived: false,
        offset: 0,
        limit: PROJECTS_PAGE_SIZE,
      }),
  });

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ProjectsPageClient />
    </HydrationBoundary>
  );
}
