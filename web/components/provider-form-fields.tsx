"use client";

import type { FieldError, UseFormRegisterReturn } from "react-hook-form";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

type ProviderFormFieldErrors = {
  label?: FieldError;
  base_url?: FieldError;
  api_key?: FieldError;
  default_model?: FieldError;
};

export function ProviderFormFields({
  labelField,
  baseUrlField,
  apiKeyField,
  defaultModelField,
  errors,
  placeholders,
  showEnabled,
  isEnabled,
  onEnabledChange,
  ids,
}: {
  labelField: UseFormRegisterReturn;
  baseUrlField: UseFormRegisterReturn;
  apiKeyField: UseFormRegisterReturn;
  defaultModelField: UseFormRegisterReturn;
  errors?: ProviderFormFieldErrors;
  placeholders?: {
    label?: string;
    baseUrl?: string;
    apiKey?: string;
    defaultModel?: string;
  };
  showEnabled?: boolean;
  isEnabled?: boolean;
  onEnabledChange?: (checked: boolean) => void;
  ids: {
    label: string;
    baseUrl: string;
    apiKey: string;
    defaultModel: string;
    isEnabled?: string;
  };
}) {
  return (
    <>
      <div className="grid gap-2">
        <Label htmlFor={ids.label}>名称</Label>
        <Input id={ids.label} placeholder={placeholders?.label} {...labelField} />
        {errors?.label?.message ? (
          <p className="text-sm text-destructive">{errors.label.message}</p>
        ) : null}
      </div>
      <div className="grid gap-2">
        <Label htmlFor={ids.baseUrl}>Base URL</Label>
        <Input id={ids.baseUrl} placeholder={placeholders?.baseUrl} {...baseUrlField} />
        {errors?.base_url?.message ? (
          <p className="text-sm text-destructive">{errors.base_url.message}</p>
        ) : null}
      </div>
      <div className="grid gap-2">
        <Label htmlFor={ids.apiKey}>API Key</Label>
        <Input
          id={ids.apiKey}
          type="password"
          placeholder={placeholders?.apiKey}
          {...apiKeyField}
        />
        {errors?.api_key?.message ? (
          <p className="text-sm text-destructive">{errors.api_key.message}</p>
        ) : null}
      </div>
      <div className="grid gap-2">
        <Label htmlFor={ids.defaultModel}>默认模型</Label>
        <Input
          id={ids.defaultModel}
          placeholder={placeholders?.defaultModel}
          {...defaultModelField}
        />
        {errors?.default_model?.message ? (
          <p className="text-sm text-destructive">{errors.default_model.message}</p>
        ) : null}
      </div>
      {showEnabled && ids.isEnabled ? (
        <div className="flex items-center space-x-2 text-muted-foreground">
          <Switch
            id={ids.isEnabled}
            checked={Boolean(isEnabled)}
            onCheckedChange={onEnabledChange}
          />
          <Label htmlFor={ids.isEnabled}>启用该配置</Label>
        </div>
      ) : null}
    </>
  );
}
