import { ConceptGachaPage } from "@/components/concept-gacha-page";
import { getServerProviderConfigs } from "@/lib/server-api";

export default async function NewProjectPage() {
  const providers = await getServerProviderConfigs();

  return <ConceptGachaPage providers={providers} />;
}
