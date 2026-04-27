"use client";

import * as React from "react";
import { type UseFormReturn } from "react-hook-form";

import { type PlotAnalysisJob, type PlotProfile } from "@/lib/types";
import { type FormValues } from "@/lib/validations/plot-lab";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { MarkdownEditorField } from "@/components/markdown-editor-field";

export const PlotLabWizardSkeletonStep = React.memo(function PlotLabWizardSkeletonStep({
  job,
  existingProfile,
  skeletonMarkdown,
  isLoading,
  isError,
  errorMessage,
  form,
  onBack,
  onNext,
}: {
  job: PlotAnalysisJob;
  existingProfile: PlotProfile | null;
  skeletonMarkdown: string | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  form: UseFormReturn<FormValues>;
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
        <CardContent className="space-y-8">
          {isLoading && !existingProfile ? <p>加载中...</p> : null}
          {isError && !existingProfile ? <p className="text-destructive">{errorMessage}</p> : null}
          {job.status === "succeeded" ? (
            <>
              <MarkdownEditorField<FormValues>
                control={form.control}
                name="plotSkeletonMarkdown"
                id="plot-skeleton-markdown"
                label="全书骨架 Markdown"
                minHeight={400}
              />
              {!skeletonMarkdown ? <p className="text-sm text-muted-foreground">当前任务暂无骨架数据，可在此补录。</p> : null}
            </>
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
