"use client";

import * as React from "react";
import { type UseFormReturn } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MarkdownEditorField } from "@/components/markdown-editor-field";
import { type ProjectSummary, type PlotAnalysisJob, type PlotProfile } from "@/lib/types";
import type { FormValues } from "@/lib/validations/plot-lab";

const NONE_VALUE = "__none__";

export const PlotLabWizardPromptPackStep = React.memo(function PlotLabWizardPromptPackStep({
  job,
  existingProfile,
  storyEngineMarkdown,
  isLoading,
  isError,
  errorMessage,
  projects,
  mountProjectId,
  setMountProjectId,
  form,
  onBack,
  onSave,
  saving,
}: {
  job: PlotAnalysisJob;
  existingProfile: PlotProfile | null;
  storyEngineMarkdown: string | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  projects: ProjectSummary[];
  mountProjectId: string | null;
  setMountProjectId: (value: string | null) => void;
  form: UseFormReturn<FormValues>;
  onBack: () => void;
  onSave: () => void;
  saving: boolean;
}) {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card>
        <CardHeader>
          <CardTitle>Story Engine 配置</CardTitle>
          <CardDescription>最后一步，直接编辑 Story Engine Profile 并保存。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading && !existingProfile ? <p>加载中...</p> : null}
          {isError && !existingProfile ? <p className="text-destructive">{errorMessage}</p> : null}
          {job.status === "succeeded" ? (
            <>
              <MarkdownEditorField<FormValues>
                control={form.control}
                name="storyEngineMarkdown"
                id="story-engine-markdown"
                label="Story Engine Markdown"
                ariaLabel="Story Engine Markdown"
                minHeight={420}
              />

              {!existingProfile ? (
                <div className="grid gap-2 p-4 bg-muted/50 rounded-lg border">
                  <Label>保存并挂载到项目 (可选)</Label>
                  <Select
                    value={mountProjectId ?? NONE_VALUE}
                    onValueChange={(value) => setMountProjectId(value === NONE_VALUE ? null : value)}
                  >
                    <SelectTrigger className="bg-background">
                      <SelectValue placeholder="仅保存为全局情节资产" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE_VALUE}>仅保存，不挂载</SelectItem>
                      {projects.map((project) => (
                        <SelectItem key={project.id} value={project.id}>
                          {project.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground mt-1">
                    如果你希望这个情节模板立即在一个写作项目生效，请选择挂载。
                  </p>
                </div>
              ) : null}
            </>
          ) : (
            <p>Story Engine 数据尚未准备好。</p>
          )}
          <div className="flex justify-between pt-4">
            <Button variant="outline" onClick={onBack}>
              上一步
            </Button>
            <Button onClick={onSave} disabled={saving}>
              {saving ? "保存中..." : "保存完成"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
});
