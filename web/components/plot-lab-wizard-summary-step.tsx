"use client";

import { useController, type UseFormReturn } from "react-hook-form";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { type PlotAnalysisJob, type PlotProfile } from "@/lib/types";
import type { FormValues } from "@/lib/validations/plot-lab";

export const PlotLabWizardSummaryStep = React.memo(function PlotLabWizardSummaryStep({
  job,
  existingProfile,
  summaryMarkdown,
  isLoading,
  isError,
  errorMessage,
  form,
  onBack,
  onNext,
}: {
  job: PlotAnalysisJob;
  existingProfile: PlotProfile | null;
  summaryMarkdown: string | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  form: UseFormReturn<FormValues>;
  onBack: () => void;
  onNext: () => void;
}) {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const { field } = useController({
    name: "plotSummaryMarkdown",
    control: form.control,
  });

  const handleRef = React.useCallback(
    (e: HTMLTextAreaElement | null) => {
      field.ref(e);
      textareaRef.current = e;
    },
    [field]
  );

  const handleInput = React.useCallback(() => {
    const target = textareaRef.current;
    if (target) {
      target.style.height = "auto";
      const nextHeight = Math.max(360, target.scrollHeight);
      target.style.height = `${nextHeight}px`;
    }
  }, []);

  React.useEffect(() => {
    handleInput();
  }, [summaryMarkdown, handleInput]);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card>
        <CardHeader>
          <CardTitle>剧情摘要编辑</CardTitle>
          <CardDescription>直接编辑 Markdown 剧情摘要，这部分将作为生成 Prompt 的核心基础。</CardDescription>
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
              <div className="grid gap-2">
                <Label htmlFor="plot-summary-markdown">剧情摘要 Markdown</Label>
                <ScrollArea className="h-[360px] w-full rounded-md border border-input bg-background" type="auto">
                  <Textarea
                    id="plot-summary-markdown"
                    className="min-h-[360px] w-full resize-none border-0 focus-visible:ring-0 focus-visible:ring-offset-0 p-4 font-mono text-sm overflow-hidden"
                    {...field}
                    value={field.value ?? ""}
                    ref={handleRef}
                    onInput={(e) => {
                      field.onChange(e);
                      handleInput();
                    }}
                  />
                </ScrollArea>
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
