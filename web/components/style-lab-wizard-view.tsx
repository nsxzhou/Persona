"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { PromptPack, PromptPackFewShotSlot, StyleSummary, StyleSummarySceneStrategy } from "@/lib/types";

// Helper functions for text area conversions
function linesToList(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function listToLines(values: string[]) {
  return values.join("\n");
}

function sceneStrategiesToLines(values: StyleSummarySceneStrategy[]) {
  return values.map((item) => `${item.scene}: ${item.instruction}`).join("\n");
}

function linesToSceneStrategies(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [scene, ...rest] = line.split(":");
      return {
        scene: scene.trim(),
        instruction: rest.join(":").trim() || "待补充说明",
      };
    });
}

function fewShotSlotsToLines(values: PromptPackFewShotSlot[]) {
  return values
    .map((item) => `${item.label}|${item.type}|${item.purpose}|${item.text}`)
    .join("\n");
}

function linesToFewShotSlots(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [label, type, purpose, ...rest] = line.split("|");
      return {
        label: label?.trim() || `slot-${index + 1}`,
        type: type?.trim() || "generic",
        purpose: purpose?.trim() || "补充风格示例",
        text: rest.join("|").trim() || line,
      };
    });
}

const NONE_VALUE = "__none__";

export function StyleLabWizardView({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [step, setStep] = React.useState<1 | 2 | 3>(1);
  const [mountProjectId, setMountProjectId] = React.useState<string | null>(null);

  // Queries
  const jobQuery = useQuery({
    queryKey: ["style-analysis-jobs", jobId],
    queryFn: () => api.getStyleAnalysisJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? 2000 : false;
    },
  });
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.getProjects(false),
  });
  const profilesQuery = useQuery({
    queryKey: ["style-profiles"],
    queryFn: () => api.getStyleProfiles(),
  });

  const job = jobQuery.data;
  const projects = projectsQuery.data ?? [];
  const existingProfile = profilesQuery.data?.find((p) => p.id === job?.style_profile_id);

  // States for forms
  const [styleSummaryState, setStyleSummaryState] = React.useState<StyleSummary | null>(null);
  const [promptPackState, setPromptPackState] = React.useState<PromptPack | null>(null);

  // Sync state when job completes
  React.useEffect(() => {
    if (job?.status === "succeeded" && job.style_summary && !styleSummaryState) {
      setStyleSummaryState(job.style_summary);
    }
    if (job?.status === "succeeded" && job.prompt_pack && !promptPackState) {
      setPromptPackState(job.prompt_pack);
    }
  }, [job, styleSummaryState, promptPackState]);

  // Sync with existing profile if it exists
  React.useEffect(() => {
    if (existingProfile) {
      if (!styleSummaryState && existingProfile.style_summary) setStyleSummaryState(existingProfile.style_summary);
      if (!promptPackState && existingProfile.prompt_pack) setPromptPackState(existingProfile.prompt_pack);
    }
  }, [existingProfile, styleSummaryState, promptPackState]);

  const saveProfileMutation = useMutation({
    mutationFn: async () => {
      if (!styleSummaryState || !promptPackState || !job) throw new Error("缺少保存数据");
      if (existingProfile) {
        const profile = await api.updateStyleProfile(existingProfile.id, {
          style_summary: styleSummaryState,
          prompt_pack: promptPackState,
        });
        if (mountProjectId) {
          await api.updateProject(mountProjectId, { style_profile_id: profile.id });
        }
        return profile;
      } else {
        const profile = await api.createStyleProfile({
          job_id: job.id,
          style_summary: styleSummaryState,
          prompt_pack: promptPackState,
        });
        if (mountProjectId) {
          await api.updateProject(mountProjectId, { style_profile_id: profile.id });
        }
        return profile;
      }
    },
    onSuccess: () => {
      toast.success("风格档案已保存");
      router.push("/style-lab");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "保存失败");
    },
  });

  if (jobQuery.isLoading || projectsQuery.isLoading) return <PageLoading title="加载中..." />;
  if (jobQuery.isError) return <PageError title="加载任务失败" message={jobQuery.error.message} />;
  if (!job) return <PageError title="任务不存在" message="未找到对应的风格分析任务" />;

  const isProcessing = job.status === "pending" || job.status === "running";
  const currentReport = job.analysis_report;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/style-lab"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{job.style_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={job.status === "failed" ? "destructive" : "secondary"}>{job.status}</Badge>
            <span className="text-sm text-muted-foreground">模型: {job.model_name}</span>
          </div>
        </div>
      </div>

      {/* Stepper */}
      <div className="flex items-center justify-center border-b pb-6">
        <div className="flex items-center gap-2">
          <div className={`flex items-center justify-center w-8 h-8 rounded-full ${step >= 1 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
            {step > 1 ? <CheckCircle2 className="w-5 h-5" /> : 1}
          </div>
          <span className={`text-sm font-medium ${step >= 1 ? "text-foreground" : "text-muted-foreground"}`}>分析报告</span>
        </div>
        <div className={`w-16 h-1 mx-2 rounded-full ${step >= 2 ? "bg-primary" : "bg-muted"}`} />
        <div className="flex items-center gap-2">
          <div className={`flex items-center justify-center w-8 h-8 rounded-full ${step >= 2 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
            {step > 2 ? <CheckCircle2 className="w-5 h-5" /> : 2}
          </div>
          <span className={`text-sm font-medium ${step >= 2 ? "text-foreground" : "text-muted-foreground"}`}>风格摘要</span>
        </div>
        <div className={`w-16 h-1 mx-2 rounded-full ${step >= 3 ? "bg-primary" : "bg-muted"}`} />
        <div className="flex items-center gap-2">
          <div className={`flex items-center justify-center w-8 h-8 rounded-full ${step >= 3 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
            3
          </div>
          <span className={`text-sm font-medium ${step >= 3 ? "text-foreground" : "text-muted-foreground"}`}>母 Prompt</span>
        </div>
      </div>

      {/* Step 1: Report */}
      {step === 1 && (
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
          ) : job.status === "failed" ? (
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
                {currentReport ? (
                  <>
                    <div className="rounded-lg border bg-zinc-50 p-4 dark:bg-zinc-900">
                      <h3 className="font-semibold text-lg mb-2">执行摘要</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">{currentReport.executive_summary.summary}</p>
                    </div>
                    <div className="space-y-4">
                      {currentReport.sections.map((section) => (
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
                  <Button onClick={() => setStep(2)}>审阅完毕，下一步</Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Step 2: Summary */}
      {step === 2 && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <Card>
            <CardHeader>
              <CardTitle>风格摘要编辑</CardTitle>
              <CardDescription>你可以在此微调 AI 提取的风格摘要。这部分将作为生成 Prompt 的核心基础。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {styleSummaryState ? (
                <>
                  <div className="grid gap-2">
                    <Label htmlFor="style-name">风格名称</Label>
                    <Input
                      id="style-name"
                      value={styleSummaryState.style_name}
                      onChange={(e) => setStyleSummaryState({ ...styleSummaryState, style_name: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="style-positioning">风格定位</Label>
                    <Textarea
                      id="style-positioning"
                      className="min-h-[100px]"
                      value={styleSummaryState.style_positioning}
                      onChange={(e) => setStyleSummaryState({ ...styleSummaryState, style_positioning: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="core-features">核心特征 (每行一项)</Label>
                    <Textarea
                      id="core-features"
                      className="min-h-[120px]"
                      value={listToLines(styleSummaryState.core_features)}
                      onChange={(e) => setStyleSummaryState({ ...styleSummaryState, core_features: linesToList(e.target.value) })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="scene-strategies">场景策略 (Key: Value)</Label>
                    <Textarea
                      id="scene-strategies"
                      className="min-h-[120px]"
                      value={sceneStrategiesToLines(styleSummaryState.scene_strategies)}
                      onChange={(e) => setStyleSummaryState({ ...styleSummaryState, scene_strategies: linesToSceneStrategies(e.target.value) })}
                    />
                  </div>
                </>
              ) : (
                <p>摘要数据尚未准备好。</p>
              )}
              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setStep(1)}>上一步</Button>
                <Button onClick={() => setStep(3)}>确认摘要，下一步</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Step 3: Prompts */}
      {step === 3 && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <Card>
            <CardHeader>
              <CardTitle>母 Prompt 包配置</CardTitle>
              <CardDescription>最后一步，配置用于全局调用的系统指令和 Few-shot 槽位。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {promptPackState ? (
                <>
                  <div className="grid gap-2">
                    <Label htmlFor="system-prompt">System Prompt</Label>
                    <Textarea
                      id="system-prompt"
                      className="min-h-[120px]"
                      value={promptPackState.system_prompt}
                      onChange={(e) => setPromptPackState({ ...promptPackState, system_prompt: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="grid gap-2">
                      <Label>对白 Prompt</Label>
                      <Textarea
                        value={promptPackState.scene_prompts.dialogue}
                        onChange={(e) => setPromptPackState({
                          ...promptPackState,
                          scene_prompts: { ...promptPackState.scene_prompts, dialogue: e.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>动作 Prompt</Label>
                      <Textarea
                        value={promptPackState.scene_prompts.action}
                        onChange={(e) => setPromptPackState({
                          ...promptPackState,
                          scene_prompts: { ...promptPackState.scene_prompts, action: e.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>环境 Prompt</Label>
                      <Textarea
                        value={promptPackState.scene_prompts.environment}
                        onChange={(e) => setPromptPackState({
                          ...promptPackState,
                          scene_prompts: { ...promptPackState.scene_prompts, environment: e.target.value },
                        })}
                      />
                    </div>
                  </div>
                  <div className="grid gap-2">
                    <Label>硬约束 (每行一项)</Label>
                    <Textarea
                      value={listToLines(promptPackState.hard_constraints)}
                      onChange={(e) => setPromptPackState({ ...promptPackState, hard_constraints: linesToList(e.target.value) })}
                    />
                  </div>
                  
                  {/* Mount Project Dropdown */}
                  {!existingProfile && (
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
                  )}

                </>
              ) : (
                <p>Prompt 数据尚未准备好。</p>
              )}
              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setStep(2)}>上一步</Button>
                <Button 
                  onClick={() => saveProfileMutation.mutate()}
                  disabled={saveProfileMutation.isPending}
                >
                  {saveProfileMutation.isPending ? "保存中..." : "保存完成"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
