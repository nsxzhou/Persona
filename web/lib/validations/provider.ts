import { z } from "zod";

import type { ProviderConfig } from "@/lib/types";

const DEFAULT_PROVIDER_BASE_URL = "https://api.openai.com/v1";
const DEFAULT_PROVIDER_MODEL = "gpt-4.1-mini";

type ProviderFormSchemaOptions = {
  requireApiKey?: boolean;
};

export function createProviderFormSchema(options: ProviderFormSchemaOptions = {}) {
  const { requireApiKey = false } = options;

  return z.object({
    label: z.string().min(1, "必填"),
    base_url: z.string().min(1, "必填").url("需为有效 URL"),
    api_key: requireApiKey
      ? z.string().trim().min(4, "必填")
      : z.string().optional(),
    default_model: z.string().min(1, "必填"),
    is_enabled: z.boolean(),
  });
}

type ProviderDefaultsSource =
  | Pick<ProviderConfig, "label" | "base_url" | "default_model" | "is_enabled">
  | null
  | undefined;

export function createProviderFormDefaults(provider?: ProviderDefaultsSource) {
  return {
    label: provider?.label ?? "",
    base_url: provider?.base_url ?? DEFAULT_PROVIDER_BASE_URL,
    api_key: "",
    default_model: provider?.default_model ?? DEFAULT_PROVIDER_MODEL,
    is_enabled: provider?.is_enabled ?? true,
  };
}
