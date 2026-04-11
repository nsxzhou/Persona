"use client";

import type { UseFormReturn } from "react-hook-form";
import { Controller } from "react-hook-form";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { TextareaListEditor } from "@/components/textarea-list-editor";
import { listToLines, linesToList } from "@/lib/style-lab-transformers";
import {
  STYLE_ANALYSIS_JOB_STATUS,
  type PromptPack,
  type Project,
  type StyleAnalysisJob,
  type StyleProfile,
  type StyleSummary,
} from "@/lib/types";

const NONE_VALUE = "__none__";

export const StyleLabWizardPromptPackStep = React.memo(function StyleLabWizardPromptPackStep({
  job,
  existingProfile,
  promptPack,
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
  job: StyleAnalysisJob;
  existingProfile: StyleProfile | null;
  promptPack: PromptPack | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  projects: Project[];
  mountProjectId: string | null;
  setMountProjectId: (value: string | null) => void;
  form: UseFormReturn<{ styleSummary: StyleSummary; promptPack: PromptPack }>;
  onBack: () => void;
  onSave: () => void;
  saving: boolean;
}) {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card>
        <CardHeader>
          <CardTitle>母 Prompt 包配置</CardTitle>
          <CardDescription>最后一步，配置用于全局调用的系统指令和 Few-shot 槽位。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading && !existingProfile ? <p>加载中...</p> : null}
          {isError && !existingProfile ? (
            <p className="text-destructive">{errorMessage}</p>
          ) : null}
          {job.status === STYLE_ANALYSIS_JOB_STATUS.SUCCEEDED ? (
            <>
              <div className="grid gap-2">
                <Label htmlFor="system-prompt">System Prompt</Label>
                <Textarea
                  id="system-prompt"
                  className="min-h-[120px]"
                  {...form.register("promptPack.system_prompt")}
                />
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="grid gap-2">
                  <Label>对白 Prompt</Label>
                  <Textarea {...form.register("promptPack.scene_prompts.dialogue")} />
                </div>
                <div className="grid gap-2">
                  <Label>动作 Prompt</Label>
                  <Textarea {...form.register("promptPack.scene_prompts.action")} />
                </div>
                <div className="grid gap-2">
                  <Label>环境 Prompt</Label>
                  <Textarea {...form.register("promptPack.scene_prompts.environment")} />
                </div>
              </div>
              <div className="grid gap-2">
                <Label>硬约束 (每行一项)</Label>
                <Controller
                  control={form.control}
                  name="promptPack.hard_constraints"
                  render={({ field }) => (
                    <TextareaListEditor
                      {...field}
                      value={field.value ?? []}
                      formatter={listToLines}
                      parser={linesToList}
                    />
                  )}
                />
              </div>

              {!existingProfile ? (
                <div className="grid gap-2 p-4 bg-muted/50 rounded-lg border">
                  <Label>保存并挂载到项目 (可选)</Label>
                  <Select
                    value={mountProjectId ?? NONE_VALUE}
                    onValueChange={(value) => setMountProjectId(value === NONE_VALUE ? null : value)}
                  >
                    <SelectTrigger className="bg-background">
                      <SelectValue placeholder="仅保存为全局风格资产" />
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
                    如果你希望这个风格立即在一个写作项目生效，请选择挂载。
                  </p>
                </div>
              ) : null}
            </>
          ) : (
            <p>Prompt 数据尚未准备好。</p>
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
