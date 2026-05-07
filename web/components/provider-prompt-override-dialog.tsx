"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { ProviderConfig } from "@/lib/types";

type ProviderPromptOverrideValues = {
  immersion_prompt_override_enabled: boolean;
  immersion_system_prompt_suffix: string;
};

export function ProviderPromptOverrideDialog({
  open,
  provider,
  submitting,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  provider: ProviderConfig | null;
  submitting: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: ProviderPromptOverrideValues) => Promise<void>;
}) {
  const [enabled, setEnabled] = useState(false);
  const [suffix, setSuffix] = useState("");

  useEffect(() => {
    setEnabled(Boolean(provider?.immersion_prompt_override_enabled));
    setSuffix(provider?.immersion_system_prompt_suffix ?? "");
  }, [provider]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Provider 提示词</DialogTitle>
          <DialogDescription>{provider?.label ?? "Provider"}</DialogDescription>
        </DialogHeader>
        <form
          className="mt-4 grid gap-5"
          onSubmit={(event) => {
            event.preventDefault();
            void onSubmit({
              immersion_prompt_override_enabled: enabled,
              immersion_system_prompt_suffix: suffix,
            });
          }}
        >
          <div className="flex items-center justify-between gap-4 rounded-md border border-border px-4 py-3">
            <Label htmlFor="provider-prompt-override-enabled">
              启用沉浸提示词追加
            </Label>
            <Switch
              id="provider-prompt-override-enabled"
              checked={enabled}
              onCheckedChange={setEnabled}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="provider-prompt-override-suffix">
              沉浸模式 System Prompt 追加内容
            </Label>
            <Textarea
              id="provider-prompt-override-suffix"
              className="min-h-[260px] resize-y font-mono text-sm leading-6"
              value={suffix}
              onChange={(event) => setSuffix(event.target.value)}
            />
          </div>
          <Button type="submit" disabled={submitting}>
            保存提示词
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
