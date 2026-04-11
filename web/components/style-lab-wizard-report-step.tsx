"use client";

import * as React from "react";

import {
  STYLE_ANALYSIS_JOB_PROCESSING_STATUSES,
  STYLE_ANALYSIS_JOB_STATUS,
  type AnalysisReport,
  type StyleAnalysisJob,
  type StyleProfile,
} from "@/lib/types";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const StyleLabWizardReportStep = React.memo(function StyleLabWizardReportStep({
  job,
  existingProfile,
  report,
  isLoading,
  isError,
  errorMessage,
  onNext,
}: {
  job: StyleAnalysisJob;
  existingProfile: StyleProfile | null;
  report: AnalysisReport | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  onNext: () => void;
}) {
  const isProcessing = STYLE_ANALYSIS_JOB_PROCESSING_STATUSES.some(
    (status) => status === job.status,
  );

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
            <p>分析失败: {job.error_message}</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>完整分析报告</CardTitle>
            <CardDescription>这是 AI 提取的原始风格分析报告，仅供审阅。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {isLoading && !existingProfile ? <p>加载中...</p> : null}
            {isError && !existingProfile ? (
              <p className="text-destructive">{errorMessage}</p>
            ) : null}
            {report ? (
              <>
                <div className="rounded-lg border bg-zinc-50 p-4 dark:bg-zinc-900">
                  <h3 className="font-semibold text-lg mb-2">执行摘要</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {report.executive_summary.summary}
                  </p>
                </div>
                <div className="space-y-4">
                  {report.sections.map((section) => (
                    <div key={section.section} className="rounded-lg border p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <Badge variant="secondary">{section.section}</Badge>
                        <h3 className="font-medium">{section.title}</h3>
                      </div>
                      <p className="text-sm text-muted-foreground mb-4">{section.overview}</p>
                      <div className="grid gap-3">
                        {section.findings.map((finding) => (
                          <div key={finding.label} className="bg-muted/50 rounded p-3 text-sm">
                            <div className="font-medium mb-1">{finding.label}</div>
                            <div className="text-muted-foreground">{finding.summary}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </>
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
