import { ProjectWorkbench } from "@/components/project-workbench";
import { getServerProject, getServerProviderConfigs, getServerStyleProfiles } from "@/lib/server-api";
import { notFound } from "next/navigation";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let project;
  try {
    project = await getServerProject(id);
  } catch {
    notFound();
  }

  const [providers, styleProfiles] = await Promise.all([
    getServerProviderConfigs(),
    getServerStyleProfiles(100),
  ]);

  return (
    <ProjectWorkbench
      project={project}
      providers={providers}
      styleProfiles={styleProfiles}
    />
  );
}
