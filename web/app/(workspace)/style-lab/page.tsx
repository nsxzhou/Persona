import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";

import { StyleLabDashboardPageView } from "@/components/lab-dashboard-page-view";
import { providerQueryKeys } from "@/lib/provider-query-keys";
import { getServerApi } from "@/lib/server-api";
import { styleLabQueryKeys } from "@/lib/style-lab-query-keys";

const PAGE_SIZE = 12;

export default async function StyleLabPage() {
  const api = await getServerApi();
  const queryClient = new QueryClient();

  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: providerQueryKeys.lists(),
      queryFn: api.getProviderConfigs,
    }),
    queryClient.prefetchQuery({
      queryKey: styleLabQueryKeys.jobs.list(1),
      queryFn: () => api.getStyleAnalysisJobs({ offset: 0, limit: PAGE_SIZE }),
    }),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <StyleLabDashboardPageView />
    </HydrationBoundary>
  );
}
