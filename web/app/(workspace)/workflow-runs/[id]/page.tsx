import { WorkflowRunDetailView } from "@/components/workflow-run-detail-view";

export default async function WorkflowRunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <WorkflowRunDetailView runId={id} />;
}

