"use client";

import * as React from "react";
import { AlertTriangle, FileText, Loader2, Pause, Play, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type {
  NovelWorkflowListItem,
  NovelWorkflowStatusSnapshot,
} from "@/lib/types";

const LOG_WINDOW_SIZE = 64 * 1024;

type Props = {
  run: NovelWorkflowListItem;
  className?: string;
  onStatusChange?: (status: NovelWorkflowStatusSnapshot) => void;
};

export function NovelWorkflowRunPanel({ run, className, onStatusChange }: Props) {
  const [status, setStatus] = React.useState<NovelWorkflowStatusSnapshot>(() => ({
    id: run.id,
    status: run.status,
    stage: run.stage,
    checkpoint_kind: run.checkpoint_kind,
    latest_artifacts: run.latest_artifacts ?? [],
    warnings: run.warnings ?? [],
    error_message: run.error_message,
    updated_at: run.updated_at,
    pause_requested_at: run.pause_requested_at,
  }));
  const [logs, setLogs] = React.useState("");
  const [logOffset, setLogOffset] = React.useState(0);
  const logOffsetRef = React.useRef(0);
  const [selectedArtifact, setSelectedArtifact] = React.useState<string | null>(
    (run.latest_artifacts ?? [])[0] ?? null,
  );
  const [artifactMarkdown, setArtifactMarkdown] = React.useState("");
  const [feedback, setFeedback] = React.useState("");
  const [isBusy, setIsBusy] = React.useState(false);

  const isProcessing = status.status === "pending" || status.status === "running";
  const canDecide = status.status === "paused" && Boolean(status.checkpoint_kind && selectedArtifact);
  const artifacts = status.latest_artifacts ?? [];

  const refreshStatus = React.useCallback(async () => {
    const next = await api.getNovelWorkflowStatus(run.id);
    setStatus(next);
    onStatusChange?.(next);
    setSelectedArtifact((current) => current ?? next.latest_artifacts?.[0] ?? null);
    return next;
  }, [onStatusChange, run.id]);

  const refreshLogs = React.useCallback(async () => {
    const requestedOffset = logOffsetRef.current;
    const payload = await api.getNovelWorkflowLogs(run.id, requestedOffset);
    if (payload.next_offset === requestedOffset && payload.content === "") return;
    if (payload.next_offset <= logOffsetRef.current && !payload.truncated) return;
    setLogs((prev) => {
      const next = payload.truncated ? payload.content : prev + payload.content;
      return next.slice(-LOG_WINDOW_SIZE);
    });
    logOffsetRef.current = payload.next_offset;
    setLogOffset(payload.next_offset);
  }, [run.id]);

  React.useEffect(() => {
    setStatus({
      id: run.id,
      status: run.status,
      stage: run.stage,
      checkpoint_kind: run.checkpoint_kind,
      latest_artifacts: run.latest_artifacts ?? [],
      warnings: run.warnings ?? [],
      error_message: run.error_message,
      updated_at: run.updated_at,
      pause_requested_at: run.pause_requested_at,
    });
    setLogs("");
    setLogOffset(0);
    logOffsetRef.current = 0;
    setSelectedArtifact((run.latest_artifacts ?? [])[0] ?? null);
    setArtifactMarkdown("");
    setFeedback("");
  }, [run]);

  React.useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  React.useEffect(() => {
    void refreshLogs();
    if (!isProcessing) return;
    const interval = window.setInterval(() => {
      void refreshLogs();
      void refreshStatus();
    }, 2000);
    return () => window.clearInterval(interval);
  }, [isProcessing, refreshLogs, refreshStatus]);

  React.useEffect(() => {
    if (!selectedArtifact) {
      setArtifactMarkdown("");
      return;
    }
    let cancelled = false;
    api.getNovelWorkflowArtifact(run.id, selectedArtifact)
      .then((markdown) => {
        if (!cancelled) setArtifactMarkdown(markdown);
      })
      .catch(() => {
        if (!cancelled) setArtifactMarkdown("");
      });
    return () => {
      cancelled = true;
    };
  }, [run.id, selectedArtifact]);

  const handlePause = React.useCallback(async () => {
    setIsBusy(true);
    try {
      const next = await api.pauseNovelWorkflow(run.id);
      setStatus(next);
      onStatusChange?.(next);
    } finally {
      setIsBusy(false);
    }
  }, [onStatusChange, run.id]);

  const handleResume = React.useCallback(async () => {
    setIsBusy(true);
    try {
      const next = await api.resumeNovelWorkflow(run.id);
      setStatus(next);
      onStatusChange?.(next);
    } finally {
      setIsBusy(false);
    }
  }, [onStatusChange, run.id]);

  const submitDecision = React.useCallback(
    async (action: "approve" | "revise") => {
      if (!selectedArtifact) return;
      setIsBusy(true);
      try {
        const next = await api.decideNovelWorkflow(run.id, {
          action,
          artifact_name: selectedArtifact,
          edited_markdown: artifactMarkdown,
          ...(action === "revise" && feedback.trim() ? { feedback: feedback.trim() } : {}),
        });
        setStatus(next);
        onStatusChange?.(next);
      } finally {
        setIsBusy(false);
      }
    },
    [artifactMarkdown, feedback, onStatusChange, run.id, selectedArtifact],
  );

  return (
    <section className={className} aria-label="工作流 run 面板">
      <div className="rounded-md border border-border bg-background">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold">工作流 run</h2>
              <Badge variant="outline">{run.intent_type}</Badge>
              <Badge variant={status.status === "failed" ? "destructive" : "secondary"}>
                {status.status}
              </Badge>
              {status.stage ? <Badge variant="outline">{status.stage}</Badge> : null}
              {status.checkpoint_kind ? <Badge variant="outline">{status.checkpoint_kind}</Badge> : null}
            </div>
            <p className="text-xs text-muted-foreground">Run ID: {run.id}</p>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => void refreshStatus()}>
              <RefreshCw className="mr-2 h-3.5 w-3.5" />
              刷新
            </Button>
            {status.status === "paused" || status.status === "failed" ? (
              <Button type="button" size="sm" onClick={handleResume} disabled={isBusy}>
                <Play className="mr-2 h-3.5 w-3.5" />
                继续
              </Button>
            ) : (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={handlePause}
                disabled={isBusy || status.status === "succeeded" || Boolean(status.pause_requested_at)}
              >
                <Pause className="mr-2 h-3.5 w-3.5" />
                {status.pause_requested_at ? "等待暂停" : "暂停"}
              </Button>
            )}
          </div>
        </div>

        <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]">
          <div className="space-y-4">
            {status.warnings?.length ? (
              <div className="space-y-2 rounded-md border border-amber-300/60 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                {status.warnings.map((warning) => (
                  <p key={warning} className="flex items-center gap-2">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    {warning}
                  </p>
                ))}
              </div>
            ) : null}

            {status.error_message ? (
              <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {status.error_message}
              </div>
            ) : null}

            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-medium text-muted-foreground">产物</span>
                {artifacts.length ? (
                  artifacts.map((artifact) => (
                    <Button
                      key={artifact}
                      type="button"
                      variant={selectedArtifact === artifact ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedArtifact(artifact)}
                    >
                      <FileText className="mr-2 h-3.5 w-3.5" />
                      {artifact}
                    </Button>
                  ))
                ) : (
                  <span className="text-xs text-muted-foreground">暂无产物</span>
                )}
              </div>
              {selectedArtifact ? (
                <Textarea
                  value={artifactMarkdown}
                  onChange={(event) => setArtifactMarkdown(event.target.value)}
                  className="min-h-[180px] font-mono text-sm"
                  aria-label={`${selectedArtifact} 产物内容`}
                />
              ) : null}
            </div>

            {canDecide ? (
              <div className="space-y-2 rounded-md border border-border bg-muted/20 p-3">
                <p className="text-sm font-medium">人工断点确认</p>
                <Textarea
                  value={feedback}
                  onChange={(event) => setFeedback(event.target.value)}
                  aria-label="修订意见"
                  placeholder="需要重跑或修订时填写意见"
                  className="min-h-[72px]"
                />
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void submitDecision("revise")}
                    disabled={isBusy}
                  >
                    {isBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    提交修订
                  </Button>
                  <Button type="button" onClick={() => void submitDecision("approve")} disabled={isBusy}>
                    批准继续
                  </Button>
                </div>
              </div>
            ) : null}
          </div>

          <div className="flex min-h-[220px] flex-col rounded-md border border-border bg-[#1e1e1e] text-[#d4d4d4]">
            <div className="border-b border-white/10 px-3 py-2 text-xs text-white/70">日志</div>
            <pre className="flex-1 overflow-auto whitespace-pre-wrap p-3 font-mono text-xs leading-relaxed">
              {logs || (isProcessing ? "正在等待系统日志..." : "暂无日志")}
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}
