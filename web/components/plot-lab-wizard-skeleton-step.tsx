"use client";

import * as React from "react";

import { type PlotAnalysisJob, type PlotProfile } from "@/lib/types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const PlotLabWizardSkeletonStep = React.memo(function PlotLabWizardSkeletonStep({
  job,
  existingProfile,
  skeletonMarkdown,
  isLoading,
  isError,
  errorMessage,
  onBack,
  onNext,
}: {
  job: PlotAnalysisJob;
  existingProfile: PlotProfile | null;
  skeletonMarkdown: string | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card>
        <CardHeader>
          <CardTitle>全书骨架</CardTitle>
          <CardDescription>
            骨架是后续分析的全局参考，可先快速审阅后再查看完整报告。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading && !existingProfile ? <p>加载中...</p> : null}
          {isError && !existingProfile ? <p className="text-destructive">{errorMessage}</p> : null}
          {job.status === "succeeded" ? (
            skeletonMarkdown ? (
              <pre className="overflow-x-auto rounded-lg border bg-zinc-50 p-4 text-sm leading-relaxed whitespace-pre-wrap text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50">
                {skeletonMarkdown}
              </pre>
            ) : (
              <p>无骨架数据。</p>
            )
          ) : (
            <p>骨架数据尚未准备好。</p>
          )}
          <div className="flex justify-between pt-4">
            <Button variant="outline" onClick={onBack}>
              上一步
            </Button>
            <Button onClick={onNext}>审阅完毕，下一步</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
});
