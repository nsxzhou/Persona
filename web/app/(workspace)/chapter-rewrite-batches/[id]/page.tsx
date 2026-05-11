import { ChapterRewriteBatchDetailView } from "@/components/chapter-rewrite-batch-detail-view";

export default async function ChapterRewriteBatchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ChapterRewriteBatchDetailView batchId={id} />;
}
