import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";

import { PlotLabDashboardPageView } from "@/components/lab-dashboard-page-view";
import { plotLabQueryKeys } from "@/lib/plot-lab-query-keys";
import { providerQueryKeys } from "@/lib/provider-query-keys";
import { getServerApi } from "@/lib/server-api";

const PAGE_SIZE = 12;

export default async function PlotLabPage() {
  const api = await getServerApi();
  const queryClient = new QueryClient();

  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: providerQueryKeys.lists(),
      queryFn: api.getProviderConfigs,
    }),
    queryClient.prefetchQuery({
      queryKey: plotLabQueryKeys.jobs.list(1),
      queryFn: () => api.getPlotAnalysisJobs({ offset: 0, limit: PAGE_SIZE }),
    }),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <PlotLabDashboardPageView />
    </HydrationBoundary>
  );
}
