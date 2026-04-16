import { ProjectWorkbench } from "@/components/project-workbench";
import { getServerApi } from "@/lib/server-api";
import { notFound } from "next/navigation";

export default async function ProjectDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams?: Promise<{
    tab?: string;
    volumeIndex?: string;
  }>;
}) {
  const { id } = await params;
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
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
      initialTab={resolvedSearchParams?.tab ?? "inspiration"}
      highlightedVolumeIndex={parseVolumeIndex(resolvedSearchParams?.volumeIndex)}
    />
  );
}

function parseVolumeIndex(value?: string) {
  if (typeof value !== "string" || value === "") return null;
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) || parsed < 0 ? null : parsed;
}
