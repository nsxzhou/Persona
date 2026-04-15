import { getServerApi } from "@/lib/server-api";
import { ZenEditorView } from "@/components/zen-editor-view";
import { notFound } from "next/navigation";

export default async function ZenEditorPage({
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

  let activeProfileName;
  if (project.style_profile_id) {
    try {
      const profile = await api.getStyleProfile(project.style_profile_id);
      activeProfileName = profile.style_name;
    } catch {
      // ignore
    }
  }

  return (
    <ZenEditorView 
      project={project} 
      activeProfileName={activeProfileName} 
    />
  );
}