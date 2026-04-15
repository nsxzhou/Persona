import { dehydrate, HydrationBoundary, QueryClient } from "@tanstack/react-query";
import { PropsWithChildren } from "react";
import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { getServerApi, getServerCurrentUser } from "@/lib/server-api";

export default async function WorkspaceLayout({ children }: PropsWithChildren) {
  const api = await getServerApi();
  const [setupStatus, currentUser] = await Promise.all([
    api.getSetupStatus(),
    getServerCurrentUser(),
  ]);
  if (!setupStatus.initialized) {
    redirect("/setup");
  }

  if (!currentUser) {
    redirect("/login");
  }

  const queryClient = new QueryClient();
  queryClient.setQueryData(["current-user"], currentUser);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <AppShell>{children}</AppShell>
    </HydrationBoundary>
  );
}
