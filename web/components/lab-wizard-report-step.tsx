"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

type LabWizardReportStepProps = {
  status: string;
  stage: string | null | undefined;
  pauseRequestedAt?: string | null;
  reportMarkdown: string | null;
  isLoading: boolean;
  isError: boolean;
  hasExistingProfile: boolean;
  errorMessage?: string;
  logs: string;
  reportDescription: string;
  formatStageLabel?: (stage: string | null | undefined) => string;
  onResume: () => void;
  resuming: boolean;
  onPause: () => void;
  pausing: boolean;
  onNext: () => void;
};

export const LabWizardReportStep = React.memo(function LabWizardReportStep({
  status,
  stage,
  pauseRequestedAt,
  reportMarkdown,
  isLoading,
  isError,
  hasExistingProfile,
  errorMessage,
  logs,
  reportDescription,
  formatStageLabel = (value) => value || "初始化",
  onResume,
  resuming,
  onPause,
  pausing,
  onNext,
}: LabWizardReportStepProps) {
  const failedMessage = errorMessage || "分析任务失败，请稍后重试。";
  const scrollAreaRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const timeoutId = setTimeout(() => {
      const viewport = scrollAreaRef.current?.querySelector(
        "[data-radix-scroll-area-viewport]",
      ) as HTMLDivElement | null;
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      }
    }, 0);
    return () => clearTimeout(timeoutId);
  }, [logs]);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {status === "pending" || status === "running" ? (
        <Card className="border-dashed border-2 bg-muted/30 overflow-hidden flex flex-col h-[500px]">
          <CardHeader className="border-b bg-muted/50 pb-4">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary" />
                正在分析中...
              </CardTitle>
              <Button variant="secondary" onClick={onPause} disabled={pausing || Boolean(pauseRequestedAt)}>
                {pausing || pauseRequestedAt ? "等待后台确认暂停..." : "暂停"}
              </Button>
            </div>
            <CardDescription>当前阶段: {formatStageLabel(stage)}</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 p-0 overflow-hidden bg-[#1e1e1e] text-[#d4d4d4] font-mono text-sm">
            <ScrollArea ref={scrollAreaRef} className="h-full w-full">
              <div className="p-4 whitespace-pre-wrap leading-relaxed">
                {logs ? (
                  <>
                    {logs}
                    <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1 align-middle" />
                  </>
                ) : (
                  <span className="text-muted-foreground">正在等待系统日志...</span>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      ) : status === "paused" ? (
        <Card className="border-muted-foreground/30 bg-muted/10">
          <CardContent className="pt-6 text-center">
            <p>任务已暂停{stage ? `（停在阶段: ${formatStageLabel(stage)}）` : ""}</p>
            <div className="mt-4 flex justify-center">
              <Button onClick={onResume} disabled={resuming}>
                {resuming ? "继续中..." : "继续任务"}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : status === "failed" ? (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="pt-6 text-center text-destructive">
            <p>分析失败: {failedMessage}</p>
            <div className="mt-4 flex justify-center">
              <Button onClick={onResume} disabled={resuming}>
                {resuming ? "恢复中..." : "恢复任务"}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>完整分析报告</CardTitle>
            <CardDescription>{reportDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {isLoading && !hasExistingProfile ? <p>加载中...</p> : null}
            {isError && !hasExistingProfile ? <p className="text-destructive">{errorMessage}</p> : null}
            {reportMarkdown ? (
              <pre className="overflow-x-auto rounded-lg border bg-zinc-50 p-4 text-sm leading-relaxed whitespace-pre-wrap text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50">
                {reportMarkdown}
              </pre>
            ) : (
              <p>无报告数据。</p>
            )}
            <div className="flex justify-end pt-4">
              <Button onClick={onNext}>审阅完毕，下一步</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
});
