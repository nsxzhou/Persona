"use client";

import type { UseFormReturn } from "react-hook-form";
import { Controller } from "react-hook-form";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { TextareaListEditor } from "@/components/textarea-list-editor";
import { listToLines, linesToList, linesToSceneStrategies, sceneStrategiesToLines } from "@/lib/style-lab-transformers";
import {
  STYLE_ANALYSIS_JOB_STATUS,
  type PromptPack,
  type StyleAnalysisJob,
  type StyleProfile,
  type StyleSummary,
} from "@/lib/types";

export const StyleLabWizardSummaryStep = React.memo(function StyleLabWizardSummaryStep({
  job,
  existingProfile,
  summary,
  isLoading,
  isError,
  errorMessage,
  form,
  onBack,
  onNext,
}: {
  job: StyleAnalysisJob;
  existingProfile: StyleProfile | null;
  summary: StyleSummary | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  form: UseFormReturn<{ styleSummary: StyleSummary; promptPack: PromptPack }>;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card>
        <CardHeader>
          <CardTitle>风格摘要编辑</CardTitle>
          <CardDescription>你可以在此微调 AI 提取的风格摘要。这部分将作为生成 Prompt 的核心基础。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading && !existingProfile ? <p>加载中...</p> : null}
          {isError && !existingProfile ? (
            <p className="text-destructive">{errorMessage}</p>
          ) : null}
          {job.status === STYLE_ANALYSIS_JOB_STATUS.SUCCEEDED ? (
            <>
              <div className="grid gap-2">
                <Label htmlFor="style-name">风格名称</Label>
                <Controller
                  control={form.control}
                  name="styleSummary.style_name"
                  render={({ field }) => <Input id="style-name" {...field} />}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="style-positioning">风格定位</Label>
                <Controller
                  control={form.control}
                  name="styleSummary.style_positioning"
                  render={({ field }) => (
                    <Textarea id="style-positioning" className="min-h-[100px]" {...field} />
                  )}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="core-features">核心特征 (每行一项)</Label>
                <Controller
                  control={form.control}
                  name="styleSummary.core_features"
                  render={({ field }) => (
                    <TextareaListEditor
                      {...field}
                      id="core-features"
                      className="min-h-[120px]"
                      value={field.value ?? []}
                      formatter={listToLines}
                      parser={linesToList}
                    />
                  )}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="scene-strategies">场景策略 (Key: Value)</Label>
                <Controller
                  control={form.control}
                  name="styleSummary.scene_strategies"
                  render={({ field }) => (
                    <TextareaListEditor
                      {...field}
                      id="scene-strategies"
                      className="min-h-[120px]"
                      value={field.value ?? []}
                      formatter={sceneStrategiesToLines}
                      parser={linesToSceneStrategies}
                    />
                  )}
                />
              </div>
            </>
          ) : (
            <p>摘要数据尚未准备好。</p>
          )}
          <div className="flex justify-between pt-4">
            <Button variant="outline" onClick={onBack}>
              上一步
            </Button>
            <Button onClick={onNext}>确认摘要，下一步</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
});
