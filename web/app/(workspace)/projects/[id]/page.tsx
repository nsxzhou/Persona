import { ProjectPageClient } from "@/components/project-form";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProjectPageClient mode="detail" projectId={id} />;
}
