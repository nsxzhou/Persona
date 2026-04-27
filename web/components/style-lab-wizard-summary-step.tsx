"use client";

import { type UseFormReturn } from "react-hook-form";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MarkdownEditorField } from "@/components/markdown-editor-field";
import { type StyleAnalysisJob, type StyleProfile } from "@/lib/types";
import type { FormValues } from "@/lib/validations/style-lab";

export const StyleLabWizardSummaryStep = React.memo(function StyleLabWizardSummaryStep({
  job,
  existingProfile,
  voiceProfileMarkdown,
  isLoading,
  isError,
  errorMessage,
  form,
  onBack,
  onNext,
}: {
  job: StyleAnalysisJob;
  existingProfile: StyleProfile | null;
  voiceProfileMarkdown: string | null;
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
          <CardTitle>Voice Profile 编辑</CardTitle>
          <CardDescription>直接编辑 Markdown Voice Profile，这部分定义"怎么写"，不定义题材推进。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          {isLoading && !existingProfile ? <p>加载中...</p> : null}
          {isError && !existingProfile ? <p className="text-destructive">{errorMessage}</p> : null}
          {job.status === "succeeded" ? (
            <>
              <div className="grid gap-2">
                <Label htmlFor="style-name">风格名称</Label>
                <Input id="style-name" {...form.register("styleName")} />
              </div>
              <MarkdownEditorField<FormValues>
                control={form.control}
                name="voiceProfileMarkdown"
                id="voice-profile-markdown"
                label="Voice Profile Markdown"
                minHeight={520}
              />
            </>
          ) : (
            <p>摘要数据尚未准备好。</p>
          )}
          <div className="flex justify-between pt-4">
            <Button variant="outline" onClick={onBack}>
              上一步
            </Button>
            <Button onClick={onNext}>确认 Voice Profile</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
});
