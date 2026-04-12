"use client";

import * as React from "react";

import {
  STYLE_ANALYSIS_JOB_PROCESSING_STATUSES,
  STYLE_ANALYSIS_JOB_STATUS,
  type StyleAnalysisJob,
  type StyleProfile,
} from "@/lib/types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const StyleLabWizardReportStep = React.memo(function StyleLabWizardReportStep({
  job,
  existingProfile,
  reportMarkdown,
  isLoading,
  isError,
  errorMessage,
  onNext,
}: {
  job: StyleAnalysisJob;
  existingProfile: StyleProfile | null;
  reportMarkdown: string | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  onNext: () => void;
}) {
  const isProcessing = STYLE_ANALYSIS_JOB_PROCESSING_STATUSES.some(
    (status) => status === job.status,
  );
  const failedMessage = job.error_message?.trim() || "分析任务失败，请稍后重试。";

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {isProcessing ? (
        <Card className="border-dashed border-2 bg-muted/30">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4" />
            <h3 className="font-medium text-lg">分析中...</h3>
            <p className="text-muted-foreground mt-2">当前阶段: {job.stage || "初始化"}</p>
            <p className="text-sm text-muted-foreground mt-1">这可能需要几分钟时间，请耐心等待。</p>
          </CardContent>
        </Card>
      ) : job.status === STYLE_ANALYSIS_JOB_STATUS.FAILED ? (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="pt-6 text-center text-destructive">
            <p>分析失败: {failedMessage}</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>完整分析报告</CardTitle>
            <CardDescription>这是 AI 生成的 Markdown 分析报告，仅供审阅。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {isLoading && !existingProfile ? <p>加载中...</p> : null}
            {isError && !existingProfile ? <p className="text-destructive">{errorMessage}</p> : null}
            {reportMarkdown ? (
              <pre className="overflow-x-auto rounded-lg border bg-zinc-50 p-4 text-sm leading-relaxed whitespace-pre-wrap dark:bg-zinc-900">
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
