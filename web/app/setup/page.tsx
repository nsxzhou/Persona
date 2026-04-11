import { redirect } from "next/navigation";

import { SetupPageClient } from "@/components/route-guards";
import { getServerCurrentUser, getServerSetupStatus } from "@/lib/server-api";

export default async function SetupPage() {
  const setupStatus = await getServerSetupStatus();
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
