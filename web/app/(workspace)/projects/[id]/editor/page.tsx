import { getServerProject, getServerStyleProfiles } from "@/lib/server-api";
import { ZenEditorView } from "@/components/zen-editor-view";
import { notFound } from "next/navigation";

export default async function ZenEditorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  
  const [project, styleProfiles] = await Promise.all([
    getServerProject(id),
    getServerStyleProfiles(100),
  ]);

  if (!project) {
    notFound();
  }

  const activeProfile = styleProfiles.find(
    (p) => p.id === project.style_profile_id
  );

  return (
    <ZenEditorView 
      project={project} 
      activeProfileName={activeProfile?.style_name} 
    />
  );
}