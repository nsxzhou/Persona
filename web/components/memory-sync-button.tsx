"use client";

import { Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { MemorySyncSource, MemorySyncStatus } from "@/lib/types";

type StatusKey = MemorySyncStatus | "checking";

type Snapshot = {
  status: MemorySyncStatus | null;
  source: MemorySyncSource | null;
  checkedAt: string | null;
  errorMessage: string | null;
};

type PillSpec = { label: string; className: string; pulse?: boolean };

const PILL_STYLES: Record<StatusKey, PillSpec> = {
  checking: {
    label: "分析中",
    className: "bg-amber-500/15 text-amber-700",
    pulse: true,
  },
  pending_review: {
    label: "待确认",
    className: "bg-orange-500/15 text-orange-700",
  },
  synced: {
    label: "已同步",
    className: "bg-emerald-500/15 text-emerald-700",
  },
  no_change: {
    label: "无更新",
    className: "bg-slate-500/10 text-slate-600",
  },
  failed: {
    label: "失败",
    className: "bg-red-500/15 text-red-700",
  },
};

function getPillSpec(snapshot: Snapshot | null, isChecking: boolean): PillSpec | null {
  if (isChecking) return PILL_STYLES.checking;
  if (!snapshot?.status) return null;
  return PILL_STYLES[snapshot.status] ?? null;
}

export function formatRelativeTime(isoDate: string | null, now: Date = new Date()): string | null {
  if (!isoDate) return null;
  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) return null;
  const delta = now.getTime() - parsed.getTime();
  if (delta < 0) return "刚刚";
  const seconds = Math.floor(delta / 1000);
  if (seconds < 45) return "刚刚";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  return parsed.toLocaleDateString();
}

function getTitleText(snapshot: Snapshot | null, isChecking: boolean): string {
  if (isChecking) return "正在检查记忆";
  if (!snapshot?.status) return "尚未同步记忆";
  switch (snapshot.status) {
    case "pending_review":
      return "记忆待确认";
    case "synced":
      return snapshot.source === "manual" ? "本章已同步记忆" : "记忆已同步";
    case "no_change":
      return snapshot.source === "manual" ? "本章无需更新" : "最近生成内容无需入记忆";
    case "failed":
      return "同步失败";
    default:
      return "记忆状态";
  }
}

function getHintText(snapshot: Snapshot | null, isChecking: boolean, disabled: boolean): string {
  if (disabled) return "选择章节后可同步记忆";
  if (isChecking) return "请稍候，正在分析是否需要更新运行时记忆";
  if (snapshot?.status === "pending_review") return "点击按钮重新打开差异对比";
  if (snapshot?.status === "failed") return "点击按钮重试同步";
  return "点击按钮整章同步最新记忆";
}

function buildTooltipText(
  snapshot: Snapshot | null,
  isChecking: boolean,
  disabled: boolean,
): string {
  const lines = [getTitleText(snapshot, isChecking)];
  const relative = formatRelativeTime(snapshot?.checkedAt ?? null);
  const sourceLabel = snapshot?.source ? (snapshot.source === "manual" ? "手动" : "自动") : null;
  if (relative || sourceLabel) {
    lines.push(`${relative ?? "尚未检查"}${sourceLabel ? ` · ${sourceLabel}` : ""}`);
  }
  if (snapshot?.status === "failed" && snapshot.errorMessage) {
    lines.push(snapshot.errorMessage);
  }
  lines.push(getHintText(snapshot, isChecking, disabled));
  return lines.join("\n");
}

export function MemorySyncButton({
  snapshot,
  isChecking,
  disabled,
  onClick,
}: {
  snapshot: Snapshot | null;
  isChecking: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const pill = getPillSpec(snapshot, isChecking);
  const buttonLabel = snapshot?.status === "failed" ? "重试同步" : "同步记忆";
  const tooltip = buildTooltipText(snapshot, isChecking, disabled);

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={onClick}
      disabled={disabled}
      title={tooltip}
      aria-label={buttonLabel}
      className="gap-2 pl-3 pr-2 h-9"
    >
      {isChecking ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Sparkles className="w-4 h-4" />
      )}
      <span className="text-sm font-medium">{buttonLabel}</span>
      {pill && (
        <span
          className={cn(
            "rounded-sm px-2 py-0.5 text-[10px] font-medium",
            pill.className,
            pill.pulse && "animate-pulse",
          )}
          data-testid="memory-sync-pill"
        >
          {pill.label}
        </span>
      )}
    </Button>
  );
}
