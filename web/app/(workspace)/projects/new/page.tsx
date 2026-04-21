import { ConceptGachaPage } from "@/components/concept-gacha-page";
import { getServerApi } from "@/lib/server-api";

export default async function NewProjectPage() {
  const api = await getServerApi();
  const [providers, styleProfiles, plotProfiles] = await Promise.all([
    api.getProviderConfigs(),
    api.getStyleProfiles({ limit: 100 }),
    api.getPlotProfiles({ limit: 100 }),
  ]);

  return <ConceptGachaPage providers={providers} styleProfiles={styleProfiles} plotProfiles={plotProfiles} />;
}
