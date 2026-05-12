import type { ReactNode } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export function PromptStackCollapsiblePanel({
  title,
  description,
  icon,
  open,
  onOpenChange,
  rightSlot,
  children,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rightSlot?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border-2 bg-card">
      <div className="flex items-center justify-between gap-4 p-4">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-start gap-3 text-left"
          onClick={() => onOpenChange(!open)}
        >
          <div className="mt-0.5">{icon}</div>
          <div className="min-w-0">
            <div className="font-semibold">{title}</div>
            <div className="mt-1 text-sm leading-5 text-muted-foreground">{description}</div>
          </div>
        </button>
        <div className="flex shrink-0 items-center gap-3">
          {rightSlot}
          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-md border-2 hover:bg-accent"
            onClick={() => onOpenChange(!open)}
            aria-label={open ? `收起${title}` : `展开${title}`}
          >
            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
        </div>
      </div>
      {open ? <div className="border-t-2 p-4">{children}</div> : null}
    </section>
  );
}

export function PromptStackEmptyPanel({
  icon,
  title,
  description,
}: {
  icon?: ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border-2 border-dashed p-4 text-sm text-muted-foreground">
      <div className="flex items-center gap-2 font-medium text-foreground">
        {icon}
        {title}
      </div>
      <p className="mt-2 leading-6">{description}</p>
    </div>
  );
}

export function PromptStackField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

export function PromptStackSwitchField({
  label,
  checked,
  onCheckedChange,
}: {
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex min-h-11 items-center gap-2 text-sm">
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
      <span>{label}</span>
    </label>
  );
}
