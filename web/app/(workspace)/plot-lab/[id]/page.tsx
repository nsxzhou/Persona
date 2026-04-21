import { PlotLabWizardView } from "@/components/plot-lab-wizard-view";

export default async function PlotLabDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  
  return <PlotLabWizardView jobId={id} />;
}
