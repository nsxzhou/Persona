import { ProjectWorkbench } from "@/components/project-workbench";
import { getServerApi } from "@/lib/server-api";
import { notFound } from "next/navigation";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const api = await getServerApi();

  let project;
  try {
    project = await api.getProject(id);
  } catch {
    notFound();
  }

  const [providers, styleProfiles] = await Promise.all([
    api.getProviderConfigs(),
    api.getStyleProfiles({ limit: 100 }),
  ]);

  return (
    <ProjectWorkbench
      project={project}
      providers={providers}
      styleProfiles={styleProfiles}
    />
  );
}
