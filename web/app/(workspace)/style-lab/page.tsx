"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
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
import type {
  StyleAnalysisJob,
  StyleDraft,
  StyleFewShotExample,
  StyleProfilePayload,
} from "@/lib/types";

const NONE_VALUE = "__none__";

function isRunningJob(job: StyleAnalysisJob | undefined) {
  return job?.status === "pending" || job?.status === "running";
}

export default function StyleLabPage() {
  const queryClient = useQueryClient();
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [styleNameInput, setStyleNameInput] = useState("");
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [modelOverride, setModelOverride] = useState("");
  const [sampleFile, setSampleFile] = useState<File | null>(null);
  const [draftState, setDraftState] = useState<StyleProfilePayload | null>(null);
  const [mountProjectId, setMountProjectId] = useState<string | null>(null);

  const providersQuery = useQuery({
    queryKey: ["provider-configs"],
    queryFn: api.getProviderConfigs,
  });
  const jobsQuery = useQuery({
    queryKey: ["style-analysis-jobs"],
    queryFn: api.getStyleAnalysisJobs,
  });
  const profilesQuery = useQuery({
    queryKey: ["style-profiles"],
    queryFn: api.getStyleProfiles,
  });
  const projectsQuery = useQuery({
    queryKey: ["projects", false],
    queryFn: () => api.getProjects(false),
  });
  const selectedJobQuery = useQuery({
    queryKey: ["style-analysis-job", selectedJobId],
    queryFn: () => api.getStyleAnalysisJob(selectedJobId!),
    enabled: Boolean(selectedJobId),
    refetchInterval: ({ state }) => {
      const job = state.data as StyleAnalysisJob | undefined;
      return isRunningJob(job) ? 1000 : false;
    },
  });

  useEffect(() => {
    if (!selectedProviderId && providersQuery.data?.length) {
      setSelectedProviderId(providersQuery.data[0].id);
    }
  }, [providersQuery.data, selectedProviderId]);

  useEffect(() => {
    if (!selectedJobId && jobsQuery.data?.length) {
      setSelectedJobId(jobsQuery.data[0].id);
      return;
    }
    if (
      selectedJobId &&
      jobsQuery.data?.length &&
      !jobsQuery.data.some((job) => job.id === selectedJobId)
    ) {
      setSelectedJobId(jobsQuery.data[0]?.id ?? null);
    }
  }, [jobsQuery.data, selectedJobId]);

  useEffect(() => {
    const selectedJob = selectedJobQuery.data;
    if (!selectedJob?.draft) {
      return;
    }
    if (draftState?.job_id === selectedJob.id) {
      return;
    }
    setDraftState({
      job_id: selectedJob.id,
      style_name: selectedJob.draft.style_name,
      analysis_summary: selectedJob.draft.analysis_summary,
      global_system_prompt: selectedJob.draft.global_system_prompt,
      dimensions: selectedJob.draft.dimensions,
      scene_prompts: selectedJob.draft.scene_prompts,
      few_shot_examples: selectedJob.draft.few_shot_examples,
    });
  }, [draftState?.job_id, selectedJobQuery.data]);

  const createJobMutation = useMutation({
    mutationFn: () => {
      if (!sampleFile) {
        throw new Error("请先选择 TXT 样本");
      }
      if (!styleNameInput.trim()) {
        throw new Error("请先填写风格档案名称");
      }
      if (!selectedProviderId) {
        throw new Error("请先选择 Provider");
      }
      return api.createStyleAnalysisJob({
        style_name: styleNameInput.trim(),
        provider_id: selectedProviderId,
        model: modelOverride.trim() || undefined,
        file: sampleFile,
      });
    },
    onError: (error) => {
      toast.error(`创建分析任务失败: ${error.message}`);
    },
    onSuccess: async () => {
      toast.success("分析任务已创建");
      setSampleFile(null);
      await queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs"] });
    },
  });

  const saveProfileMutation = useMutation({
    mutationFn: async () => {
      if (!draftState) {
        throw new Error("当前没有可保存的风格草案");
      }
      const profile = await api.createStyleProfile(draftState);
      if (mountProjectId) {
        await api.updateProject(mountProjectId, { style_profile_id: profile.id });
      }
      return profile;
    },
    onError: (error) => {
      toast.error(`保存风格档案失败: ${error.message}`);
    },
    onSuccess: async (profile) => {
      toast.success(mountProjectId ? "风格档案已保存并挂载" : "风格档案已保存");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["style-profiles"] }),
        queryClient.invalidateQueries({ queryKey: ["projects", false] }),
      ]);
      setMountProjectId(null);
      setDraftState((current) => current ? { ...current, job_id: profile.source_job_id } : current);
    },
  });

  if (
    providersQuery.isLoading ||
    jobsQuery.isLoading ||
    profilesQuery.isLoading ||
    projectsQuery.isLoading
  ) {
    return <PageLoading title="正在载入 Style Lab..." />;
  }

  if (
    providersQuery.isError ||
    jobsQuery.isError ||
    profilesQuery.isError ||
    projectsQuery.isError ||
    !providersQuery.data ||
    !jobsQuery.data ||
    !profilesQuery.data ||
    !projectsQuery.data
  ) {
    return (
      <PageError
        title="Style Lab 加载失败"
        message={
          (providersQuery.error instanceof Error && providersQuery.error.message) ||
          (jobsQuery.error instanceof Error && jobsQuery.error.message) ||
          (profilesQuery.error instanceof Error && profilesQuery.error.message) ||
          (projectsQuery.error instanceof Error && projectsQuery.error.message) ||
          "请重试"
        }
      />
    );
  }

  const providers = providersQuery.data;
  const jobs = jobsQuery.data;
  const selectedJob = selectedJobQuery.data ?? jobs.find((job) => job.id === selectedJobId) ?? null;
  const projects = projectsQuery.data;

  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Style Lab</h1>
        <p className="text-sm text-muted-foreground">
          上传单个 TXT 样本，生成可编辑的风格草案，再保存为全局风格档案并挂载到项目。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>新建分析任务</CardTitle>
          <CardDescription>首版采用单文件、单任务、单档案闭环。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="style-name-input">风格档案名称</Label>
            <Input
              id="style-name-input"
              aria-label="风格档案名称"
              value={styleNameInput}
              onChange={(event) => setStyleNameInput(event.target.value)}
              placeholder="例如：金庸武侠风"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="style-provider-select">Provider</Label>
            <Select value={selectedProviderId} onValueChange={setSelectedProviderId}>
              <SelectTrigger id="style-provider-select" aria-label="Provider" className="bg-background">
                <SelectValue placeholder="选择 Provider" />
              </SelectTrigger>
              <SelectContent className="border shadow-md rounded-md bg-popover text-popover-foreground">
                {providers.map((provider) => (
                  <SelectItem key={provider.id} value={provider.id} className="cursor-pointer">
                    {provider.label} / {provider.default_model}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="style-model-override">模型覆盖</Label>
            <Input
              id="style-model-override"
              aria-label="模型覆盖"
              value={modelOverride}
              onChange={(event) => setModelOverride(event.target.value)}
              placeholder="留空则使用 Provider 默认模型"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="style-sample-file">TXT 样本</Label>
            <Input
              id="style-sample-file"
              aria-label="TXT 样本"
              type="file"
              accept=".txt,text/plain"
              onChange={(event) => setSampleFile(event.target.files?.[0] ?? null)}
            />
          </div>
          <div className="lg:col-span-2 flex justify-end">
            <Button
              type="button"
              onClick={() => createJobMutation.mutate()}
              disabled={createJobMutation.isPending}
            >
              开始分析
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>分析任务</CardTitle>
            <CardDescription>查看最近任务状态并切换当前草案。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {jobs.length === 0 ? (
              <p className="text-sm text-muted-foreground">还没有分析任务，先上传一个 TXT 样本。</p>
            ) : (
              jobs.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => setSelectedJobId(job.id)}
                  className={`w-full rounded-lg border px-4 py-3 text-left transition-colors ${
                    selectedJobId === job.id ? "border-foreground bg-zinc-50" : "border-border hover:bg-accent/40"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-foreground">{job.style_name}</span>
                    <Badge variant={job.status === "failed" ? "outline" : "secondary"}>{job.status}</Badge>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    <div>{job.sample_file.original_filename}</div>
                    <div>{job.model_name}</div>
                  </div>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>任务详情</CardTitle>
              <CardDescription>
                {selectedJob ? "查看当前任务的阶段、错误和样本元信息。" : "选择左侧任务查看详情。"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {!selectedJob ? (
                <p className="text-muted-foreground">暂无选中任务。</p>
              ) : (
                <>
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge variant={selectedJob.status === "failed" ? "outline" : "secondary"}>
                      {selectedJob.status}
                    </Badge>
                    {selectedJob.stage ? <span className="text-muted-foreground">当前阶段：{selectedJob.stage}</span> : null}
                  </div>
                  <div className="grid gap-2 text-muted-foreground md:grid-cols-2">
                    <div>样本文件：<span className="text-foreground">{selectedJob.sample_file.original_filename}</span></div>
                    <div>字符数：<span className="text-foreground">{selectedJob.sample_file.character_count ?? "待分析"}</span></div>
                    <div>Provider：<span className="text-foreground">{selectedJob.provider.label}</span></div>
                    <div>模型：<span className="text-foreground">{selectedJob.model_name}</span></div>
                  </div>
                  {selectedJob.error_message ? (
                    <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-destructive">
                      {selectedJob.error_message}
                    </p>
                  ) : null}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>风格草案编辑</CardTitle>
              <CardDescription>
                {draftState ? "先修订草案，再保存为正式风格档案。" : "任务成功后，这里会出现可编辑草案。"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!draftState ? (
                <p className="text-sm text-muted-foreground">当前没有可编辑草案。</p>
              ) : (
                <>
                  <div className="grid gap-2">
                    <Label htmlFor="draft-style-name">风格名称</Label>
                    <Input
                      id="draft-style-name"
                      aria-label="风格名称"
                      value={draftState.style_name}
                      onChange={(event) => setDraftState({ ...draftState, style_name: event.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="draft-summary">分析摘要</Label>
                    <Textarea
                      id="draft-summary"
                      aria-label="分析摘要"
                      className="min-h-[96px]"
                      value={draftState.analysis_summary}
                      onChange={(event) => setDraftState({ ...draftState, analysis_summary: event.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="draft-system-prompt">系统提示词</Label>
                    <Textarea
                      id="draft-system-prompt"
                      aria-label="系统提示词"
                      className="min-h-[120px]"
                      value={draftState.global_system_prompt}
                      onChange={(event) => setDraftState({ ...draftState, global_system_prompt: event.target.value })}
                    />
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="grid gap-2">
                      <Label htmlFor="draft-vocabulary">词汇习惯</Label>
                      <Textarea
                        id="draft-vocabulary"
                        aria-label="词汇习惯"
                        value={draftState.dimensions.vocabulary_habits}
                        onChange={(event) => setDraftState({
                          ...draftState,
                          dimensions: { ...draftState.dimensions, vocabulary_habits: event.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="draft-rhythm">句法节奏</Label>
                      <Textarea
                        id="draft-rhythm"
                        aria-label="句法节奏"
                        value={draftState.dimensions.syntax_rhythm}
                        onChange={(event) => setDraftState({
                          ...draftState,
                          dimensions: { ...draftState.dimensions, syntax_rhythm: event.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="draft-perspective">叙事视角</Label>
                      <Textarea
                        id="draft-perspective"
                        aria-label="叙事视角"
                        value={draftState.dimensions.narrative_perspective}
                        onChange={(event) => setDraftState({
                          ...draftState,
                          dimensions: { ...draftState.dimensions, narrative_perspective: event.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="draft-dialogue-traits">对白特点</Label>
                      <Textarea
                        id="draft-dialogue-traits"
                        aria-label="对白特点"
                        value={draftState.dimensions.dialogue_traits}
                        onChange={(event) => setDraftState({
                          ...draftState,
                          dimensions: { ...draftState.dimensions, dialogue_traits: event.target.value },
                        })}
                      />
                    </div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="grid gap-2">
                      <Label htmlFor="draft-dialogue-prompt">对白提示</Label>
                      <Textarea
                        id="draft-dialogue-prompt"
                        aria-label="对白提示"
                        value={draftState.scene_prompts.dialogue}
                        onChange={(event) => setDraftState({
                          ...draftState,
                          scene_prompts: { ...draftState.scene_prompts, dialogue: event.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="draft-action-prompt">动作提示</Label>
                      <Textarea
                        id="draft-action-prompt"
                        aria-label="动作提示"
                        value={draftState.scene_prompts.action}
                        onChange={(event) => setDraftState({
                          ...draftState,
                          scene_prompts: { ...draftState.scene_prompts, action: event.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="draft-environment-prompt">环境提示</Label>
                      <Textarea
                        id="draft-environment-prompt"
                        aria-label="环境提示"
                        value={draftState.scene_prompts.environment}
                        onChange={(event) => setDraftState({
                          ...draftState,
                          scene_prompts: { ...draftState.scene_prompts, environment: event.target.value },
                        })}
                      />
                    </div>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="draft-mount-project">挂载到项目</Label>
                    <Select
                      value={mountProjectId ?? NONE_VALUE}
                      onValueChange={(value) => setMountProjectId(value === NONE_VALUE ? null : value)}
                    >
                      <SelectTrigger id="draft-mount-project" aria-label="挂载到项目" className="bg-background">
                        <SelectValue placeholder="保存为全局资产，不立即挂载" />
                      </SelectTrigger>
                      <SelectContent className="border shadow-md rounded-md bg-popover text-popover-foreground">
                        <SelectItem value={NONE_VALUE} className="cursor-pointer">仅保存，不挂载</SelectItem>
                        {projects.map((project) => (
                          <SelectItem key={project.id} value={project.id} className="cursor-pointer">
                            {project.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-3">
                    {draftState.few_shot_examples.map((example, index) => (
                      <div key={`${example.type}-${index}`} className="grid gap-2 rounded-lg border border-border p-3">
                        <Label htmlFor={`few-shot-${index}`}>Few-shot 示例 {index + 1}</Label>
                        <Input
                          id={`few-shot-type-${index}`}
                          aria-label={`Few-shot 类型 ${index + 1}`}
                          value={example.type}
                          onChange={(event) => {
                            const nextExamples = draftState.few_shot_examples.slice();
                            nextExamples[index] = { ...nextExamples[index], type: event.target.value };
                            setDraftState({ ...draftState, few_shot_examples: nextExamples });
                          }}
                        />
                        <Textarea
                          id={`few-shot-${index}`}
                          aria-label={`Few-shot 示例 ${index + 1}`}
                          value={example.text}
                          onChange={(event) => {
                            const nextExamples: StyleFewShotExample[] = draftState.few_shot_examples.slice();
                            nextExamples[index] = { ...nextExamples[index], text: event.target.value };
                            setDraftState({ ...draftState, few_shot_examples: nextExamples });
                          }}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-end">
                    <Button
                      type="button"
                      onClick={() => saveProfileMutation.mutate()}
                      disabled={saveProfileMutation.isPending}
                    >
                      保存并挂载
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}

