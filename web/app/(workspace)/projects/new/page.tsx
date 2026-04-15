import { ConceptGachaPage } from "@/components/concept-gacha-page";
import { getServerApi } from "@/lib/server-api";

export default async function NewProjectPage() {
  const api = await getServerApi();
  const providers = await api.getProviderConfigs();

  return <ConceptGachaPage providers={providers} />;
}
