import { redirect } from "next/navigation";

import { LoginPageClient } from "@/components/route-guards";
import { getServerCurrentUser, getServerSetupStatus } from "@/lib/server-api";

export default async function LoginPage() {
  const setupStatus = await getServerSetupStatus();
  if (!setupStatus.initialized) {
    redirect("/setup");
    return null;
  }

  const currentUser = await getServerCurrentUser();
  if (currentUser) {
    redirect("/projects");
    return null;
  }

  return <LoginPageClient />;
}
