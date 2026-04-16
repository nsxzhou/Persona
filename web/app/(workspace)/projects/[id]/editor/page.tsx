import { getServerApi } from "@/lib/server-api";
import { ZenEditorView } from "@/components/zen-editor-view";
import { notFound } from "next/navigation";

export default async function ZenEditorPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams?: Promise<{
    volumeIndex?: string;
    chapterIndex?: string;
    intent?: string;
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

  let activeProfileName;
  if (project.style_profile_id) {
    try {
      const profile = await api.getStyleProfile(project.style_profile_id);
      activeProfileName = profile.style_name;
    } catch {
      // ignore
    }
  }

  const volumeIndex = parseSearchParamIndex(resolvedSearchParams?.volumeIndex);
  const chapterIndex = parseSearchParamIndex(resolvedSearchParams?.chapterIndex);
  const initialChapterSelection =
    volumeIndex !== null && chapterIndex !== null
      ? { volumeIndex, chapterIndex }
      : null;
  const initialIntent =
    resolvedSearchParams?.intent === "navigate" || resolvedSearchParams?.intent === "generate_beats"
      ? resolvedSearchParams.intent
      : null;

  return (
    <ZenEditorView 
      project={project} 
      activeProfileName={activeProfileName} 
      initialChapterSelection={initialChapterSelection}
      initialIntent={initialIntent}
    />
  );
}

function parseSearchParamIndex(value?: string) {
  if (typeof value !== "string" || value === "") return null;
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) || parsed < 0 ? null : parsed;
}
