"use client";

import * as React from "react";
import { type UseFormReturn } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MarkdownEditorField } from "@/components/markdown-editor-field";
import { type PlotAnalysisJob, type PlotProfile } from "@/lib/types";
import type { FormValues } from "@/lib/validations/plot-lab";

export const PlotLabWizardSummaryStep = React.memo(function PlotLabWizardSummaryStep({
  job,
  existingProfile,
  storyEngineMarkdown,
  isLoading,
  isError,
  errorMessage,
  form,
  onBack,
  onNext,
}: {
  job: PlotAnalysisJob;
  existingProfile: PlotProfile | null;
  storyEngineMarkdown: string | null;
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
          <CardTitle>Story Engine Profile 编辑</CardTitle>
          <CardDescription>直接编辑 Story Engine Profile，定义这类书靠什么推进追读。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading && !existingProfile ? <p>加载中...</p> : null}
          {isError && !existingProfile ? <p className="text-destructive">{errorMessage}</p> : null}
          {job.status === "succeeded" ? (
            <>
              <div className="grid gap-2">
                <Label htmlFor="plot-name">情节档案名称</Label>
                <Input id="plot-name" {...form.register("plotName")} />
              </div>
              <MarkdownEditorField<FormValues>
                control={form.control}
                name="storyEngineMarkdown"
                id="story-engine-markdown"
                label="Story Engine Markdown"
                minHeight={360}
              />
            </>
          ) : (
            <p>摘要数据尚未准备好。</p>
          )}
          <div className="flex justify-between pt-4">
            <Button variant="outline" onClick={onBack}>
              上一步
            </Button>
            <Button onClick={onNext}>确认 Story Engine</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
});
