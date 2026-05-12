import { AlertCircle, CheckCircle2, CircleDot, Loader2 } from "lucide-react";

import type { ChapterRewriteItem } from "@/hooks/use-chapter-enrichment-rewrite";
import { cn } from "@/lib/utils";

export const STATE_LABEL: Record<ChapterRewriteItem["state"], string> = {
  waiting: "等待",
  running: "运行中",
  generated: "已生成",
  failed: "失败",
  applying: "应用中",
  applied: "已应用",
  apply_failed: "应用失败",
};

export const STATE_TONE: Record<ChapterRewriteItem["state"], string> = {
  waiting: "border-border bg-muted/30 text-muted-foreground",
  running: "border-blue-200 bg-blue-50 text-blue-800",
  generated: "border-emerald-200 bg-emerald-50 text-emerald-800",
  failed: "border-red-200 bg-red-50 text-red-800",
  applying: "border-blue-200 bg-blue-50 text-blue-800",
  applied: "border-slate-200 bg-slate-50 text-slate-600",
  apply_failed: "border-red-200 bg-red-50 text-red-800",
};

export function StatusPill({
  label,
  value,
  suffix,
  tone = "neutral",
}: {
  label: string;
  value: number;
  suffix?: string;
  tone?: "neutral" | "success" | "danger";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1",
        tone === "success" && "border-emerald-200 bg-emerald-50 text-emerald-800",
        tone === "danger" && "border-red-200 bg-red-50 text-red-800",
        tone === "neutral" && "border-border bg-muted/40 text-muted-foreground",
      )}
    >
      <span>{label}</span>
      <span className="font-semibold tabular-nums text-foreground">{value}{suffix}</span>
    </span>
  );
}

export function StateBadge({ state }: { state: ChapterRewriteItem["state"] }) {
  const Icon =
    state === "generated" || state === "applied"
      ? CheckCircle2
      : state === "failed" || state === "apply_failed"
        ? AlertCircle
        : state === "running" || state === "applying"
          ? Loader2
          : CircleDot;
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        STATE_TONE[state],
      )}
    >
      <Icon
        className={cn(
          "h-3 w-3",
          (state === "running" || state === "applying") && "animate-spin",
        )}
      />
      {STATE_LABEL[state]}
    </span>
  );
}
