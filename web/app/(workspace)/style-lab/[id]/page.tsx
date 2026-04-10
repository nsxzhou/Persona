import { StyleLabWizardView } from "@/components/style-lab-wizard-view";

export default async function StyleLabDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  
  return <StyleLabWizardView jobId={id} />;
}
