import { ProjectPageClient } from "@/components/project-form";
import { getServerProviderConfigs, getServerStyleProfiles } from "@/lib/server-api";

export default async function NewProjectPage() {
  const [providers, styleProfiles] = await Promise.all([
    getServerProviderConfigs(),
    getServerStyleProfiles(100),
  ]);

  return <ProjectPageClient mode="new" initialProviders={providers} initialStyleProfiles={styleProfiles} />;
}
