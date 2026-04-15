import { redirect } from "next/navigation";

import { SetupPageClient } from "@/components/route-guards";
import { getServerApi, getServerCurrentUser } from "@/lib/server-api";

export default async function SetupPage() {
  const api = await getServerApi();
  const setupStatus = await api.getSetupStatus().catch(() => ({ initialized: false }));
  if (setupStatus.initialized) {
    const currentUser = await getServerCurrentUser();
    if (currentUser) {
      redirect("/projects");
      return null;
    }
    redirect("/login");
    return null;
  }

  return <SetupPageClient />;
}
