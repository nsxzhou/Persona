import { redirect } from "next/navigation";

import { LoginPageClient } from "@/components/route-guards";
import { getServerApi, getServerCurrentUser } from "@/lib/server-api";

export default async function LoginPage() {
  const api = await getServerApi();
  const setupStatus = await api.getSetupStatus().catch(() => ({ initialized: false }));
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
