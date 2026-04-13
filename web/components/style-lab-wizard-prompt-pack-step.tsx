"use client";

import type { UseFormReturn } from "react-hook-form";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { type Project, type StyleAnalysisJob, type StyleProfile } from "@/lib/types";
import type { FormValues } from "@/lib/validations/style-lab";

const NONE_VALUE = "__none__";

export const StyleLabWizardPromptPackStep = React.memo(function StyleLabWizardPromptPackStep({
  job,
  existingProfile,
  promptPackMarkdown,
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
  promptPackMarkdown: string | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  projects: Project[];
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
          <CardTitle>母 Prompt 包配置</CardTitle>
          <CardDescription>最后一步，直接编辑 Markdown 风格母 Prompt 包。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {isLoading && !existingProfile ? <p>加载中...</p> : null}
          {isError && !existingProfile ? <p className="text-destructive">{errorMessage}</p> : null}
          {job.status === "succeeded" ? (
            <>
              <div className="grid gap-2">
                <Label htmlFor="prompt-pack-markdown">Prompt Pack Markdown</Label>
                <Textarea
                  id="prompt-pack-markdown"
                  className="min-h-[420px] font-mono text-sm"
                  defaultValue={promptPackMarkdown ?? ""}
                  {...form.register("promptPackMarkdown")}
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
