import { ProjectPageClient } from "@/components/project-form";
import { getServerProject, getServerProviderConfigs, getServerStyleProfiles } from "@/lib/server-api";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  
  const [project, providers, styleProfiles] = await Promise.all([
    getServerProject(id),
    getServerProviderConfigs(),
    getServerStyleProfiles(100),
  ]);

  return (
    <ProjectPageClient 
      mode="detail" 
      projectId={id} 
      initialProject={project}
      initialProviders={providers}
      initialStyleProfiles={styleProfiles}
    />
  );
}
