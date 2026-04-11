import { PropsWithChildren } from "react";
import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { getServerCurrentUser, getServerSetupStatus } from "@/lib/server-api";

export default async function WorkspaceLayout({ children }: PropsWithChildren) {
  const setupStatus = await getServerSetupStatus();
  if (!setupStatus.initialized) {
    redirect("/setup");
  }

  const currentUser = await getServerCurrentUser();
  if (!currentUser) {
    redirect("/login");
  }

  return <AppShell>{children}</AppShell>;
}
