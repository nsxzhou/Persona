export type User = {
  id: string;
  username: string;
  created_at: string;
};

export type ProviderConfig = {
  id: string;
  label: string;
  base_url: string;
  default_model: string;
  api_key_hint: string;
  is_enabled: boolean;
  last_test_status: string | null;
  last_test_error: string | null;
  last_tested_at: string | null;
  created_at?: string;
  updated_at?: string;
};

export type ProviderSummary = {
  id: string;
  label: string;
  base_url: string;
  default_model: string;
  is_enabled: boolean;
};

export type Project = {
  id: string;
  name: string;
  description: string;
  status: "draft" | "active" | "paused";
  default_provider_id?: string;
  default_model: string;
  style_profile_id: string | null;
  archived_at: string | null;
  created_at?: string;
  updated_at?: string;
  provider: ProviderSummary;
};

export type SetupPayload = {
  username: string;
  password: string;
  provider: {
    label: string;
    base_url: string;
    api_key: string;
    default_model: string;
    is_enabled: boolean;
  };
};

export type LoginPayload = {
  username: string;
  password: string;
};

export type ProjectPayload = {
  name: string;
  description: string;
  status: "draft" | "active" | "paused";
  default_provider_id: string;
  default_model?: string;
  style_profile_id: string | null;
};

export type ProviderPayload = {
  label: string;
  base_url: string;
  api_key?: string;
  default_model: string;
  is_enabled: boolean;
};

