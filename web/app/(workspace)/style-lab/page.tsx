"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
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
  PromptPack,
  PromptPackFewShotSlot,
  StyleAnalysisJob,
  StyleProfile,
  StyleSummary,
  StyleSummarySceneStrategy,
} from "@/lib/types";

const NONE_VALUE = "__none__";

function isRunningJob(job: StyleAnalysisJob | undefined) {
  return job?.status === "pending" || job?.status === "running";
}

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

export default function StyleLabPage() {
  const queryClient = useQueryClient();
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [styleNameInput, setStyleNameInput] = useState("");
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [modelOverride, setModelOverride] = useState("");
  const [sampleFile, setSampleFile] = useState<File | null>(null);
  const [styleSummaryState, setStyleSummaryState] = useState<StyleSummary | null>(null);
  const [promptPackState, setPromptPackState] = useState<PromptPack | null>(null);
  const [mountProjectId, setMountProjectId] = useState<string | null>(null);
  const [editorSourceKey, setEditorSourceKey] = useState<string | null>(null);

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

  const providers = providersQuery.data;
  const jobs = jobsQuery.data;
  const profiles = profilesQuery.data;
  const projects = projectsQuery.data;
  const selectedJob = useMemo(
    () => selectedJobQuery.data ?? jobs?.find((job) => job.id === selectedJobId) ?? null,
    [jobs, selectedJobId, selectedJobQuery.data],
  );
  const selectedProfile = useMemo(
    () => profiles?.find((profile) => profile.id === selectedJob?.style_profile_id) ?? null,
    [profiles, selectedJob?.style_profile_id],
  );
  const currentReport = selectedProfile?.analysis_report ?? selectedJob?.analysis_report ?? null;
  const nextEditorSourceKey = selectedProfile
    ? `profile:${selectedProfile.id}:${selectedProfile.updated_at}`
    : selectedJob?.style_summary && selectedJob?.prompt_pack
      ? `job:${selectedJob.id}:${selectedJob.updated_at}`
      : null;

  useEffect(() => {
    if (nextEditorSourceKey === editorSourceKey) {
      return;
    }

    const nextSummary = selectedProfile?.style_summary ?? selectedJob?.style_summary ?? null;
    const nextPromptPack = selectedProfile?.prompt_pack ?? selectedJob?.prompt_pack ?? null;
    setStyleSummaryState(nextSummary);
    setPromptPackState(nextPromptPack);
    setEditorSourceKey(nextEditorSourceKey);
  }, [
    editorSourceKey,
    nextEditorSourceKey,
    selectedJob?.prompt_pack,
    selectedJob?.style_summary,
    selectedProfile,
  ]);

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
      if (!selectedJob) {
        throw new Error("当前没有可保存的分析任务");
      }
      if (!styleSummaryState || !promptPackState) {
        throw new Error("当前没有可保存的分析结果");
      }

      if (selectedProfile) {
        const profile = await api.updateStyleProfile(selectedProfile.id, {
          style_summary: styleSummaryState,
          prompt_pack: promptPackState,
        });
        if (mountProjectId) {
          await api.updateProject(mountProjectId, { style_profile_id: profile.id });
        }
        return profile;
      }

      const profile = await api.createStyleProfile({
        job_id: selectedJob.id,
        style_summary: styleSummaryState,
        prompt_pack: promptPackState,
      });
      if (mountProjectId) {
        await api.updateProject(mountProjectId, { style_profile_id: profile.id });
      }
      return profile;
    },
    onError: (error) => {
      toast.error(`保存分析结果失败: ${error.message}`);
    },
    onSuccess: async () => {
      toast.success(mountProjectId ? "分析结果已保存并挂载" : "分析结果已保存");
      setMountProjectId(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["style-profiles"] }),
        queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["style-analysis-job", selectedJobId] }),
        queryClient.invalidateQueries({ queryKey: ["projects", false] }),
      ]);
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
    !providers ||
    !jobs ||
    !profiles ||
    !projects
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

  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold tracking-tight">Style Lab</h1>
        <p className="text-sm text-muted-foreground">
          上传单个 TXT 样本，生成完整分析报告、可编辑风格摘要和可复用风格母 Prompt 包。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>新建分析任务</CardTitle>
          <CardDescription>先生成完整分析，再决定是否保存为风格资产。</CardDescription>
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
            <CardDescription>选择任务后查看分析报告和当前生效稿。</CardDescription>
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
                {selectedJob ? "查看当前任务状态、判定结果和样本元信息。" : "选择左侧任务查看详情。"}
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
                    <div>文本类型：<span className="text-foreground">{selectedJob.analysis_meta?.text_type ?? "待判定"}</span></div>
                    <div>索引方式：<span className="text-foreground">{selectedJob.analysis_meta?.location_indexing ?? "待判定"}</span></div>
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
              <CardTitle>完整分析报告</CardTitle>
              <CardDescription>该部分只读，作为风格分析的审阅与复核依据。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!currentReport ? (
                <p className="text-sm text-muted-foreground">当前任务还没有生成完整分析报告。</p>
              ) : (
                <>
                  <div className="rounded-lg border border-border p-4">
                    <h3 className="font-medium">执行摘要</h3>
                    <p className="mt-2 text-sm text-muted-foreground">{currentReport.executive_summary.summary}</p>
                  </div>
                  <div className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
                    <div>文本类型：<span className="text-foreground">{currentReport.basic_assessment.text_type}</span></div>
                    <div>多说话人：<span className="text-foreground">{currentReport.basic_assessment.multi_speaker ? "是" : "否"}</span></div>
                    <div>批处理：<span className="text-foreground">{currentReport.basic_assessment.batch_mode ? "是" : "否"}</span></div>
                    <div>索引方式：<span className="text-foreground">{currentReport.basic_assessment.location_indexing}</span></div>
                  </div>
                  <div className="space-y-3">
                    {currentReport.sections.map((section) => (
                      <div key={section.section} className="rounded-lg border border-border p-4">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{section.section}</Badge>
                          <h3 className="font-medium">{section.title}</h3>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">{section.overview}</p>
                        {section.findings.map((finding) => (
                          <div key={finding.label} className="mt-3 rounded-md bg-zinc-50 p-3 text-sm">
                            <div className="font-medium">{finding.label}</div>
                            <div className="mt-1 text-muted-foreground">{finding.summary}</div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>风格摘要</CardTitle>
              <CardDescription>这是后续生成最常用的人工微调层。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!styleSummaryState ? (
                <p className="text-sm text-muted-foreground">当前没有可编辑的风格摘要。</p>
              ) : (
                <>
                  <div className="grid gap-2">
                    <Label htmlFor="summary-style-name">风格名称</Label>
                    <Input
                      id="summary-style-name"
                      aria-label="风格名称"
                      value={styleSummaryState.style_name}
                      onChange={(event) => setStyleSummaryState({ ...styleSummaryState, style_name: event.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="summary-positioning">风格定位</Label>
                    <Textarea
                      id="summary-positioning"
                      aria-label="风格定位"
                      value={styleSummaryState.style_positioning}
                      onChange={(event) => setStyleSummaryState({ ...styleSummaryState, style_positioning: event.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="summary-core-features">核心特征</Label>
                    <Textarea
                      id="summary-core-features"
                      aria-label="核心特征"
                      value={listToLines(styleSummaryState.core_features)}
                      onChange={(event) => setStyleSummaryState({ ...styleSummaryState, core_features: linesToList(event.target.value) })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="summary-scene-strategies">场景策略</Label>
                    <Textarea
                      id="summary-scene-strategies"
                      aria-label="场景策略"
                      value={sceneStrategiesToLines(styleSummaryState.scene_strategies)}
                      onChange={(event) => setStyleSummaryState({ ...styleSummaryState, scene_strategies: linesToSceneStrategies(event.target.value) })}
                    />
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>风格母 Prompt 包</CardTitle>
              <CardDescription>项目真正写作时，将在这里的全局风格包之上叠加剧情和人物上下文。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!promptPackState ? (
                <p className="text-sm text-muted-foreground">当前没有可编辑的 Prompt 包。</p>
              ) : (
                <>
                  <div className="grid gap-2">
                    <Label htmlFor="prompt-system">System Prompt</Label>
                    <Textarea
                      id="prompt-system"
                      aria-label="System Prompt"
                      className="min-h-[120px]"
                      value={promptPackState.system_prompt}
                      onChange={(event) => setPromptPackState({ ...promptPackState, system_prompt: event.target.value })}
                    />
                  </div>
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="grid gap-2">
                      <Label htmlFor="prompt-dialogue">对白 Prompt</Label>
                      <Textarea
                        id="prompt-dialogue"
                        aria-label="对白 Prompt"
                        value={promptPackState.scene_prompts.dialogue}
                        onChange={(event) => setPromptPackState({
                          ...promptPackState,
                          scene_prompts: { ...promptPackState.scene_prompts, dialogue: event.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="prompt-action">动作 Prompt</Label>
                      <Textarea
                        id="prompt-action"
                        aria-label="动作 Prompt"
                        value={promptPackState.scene_prompts.action}
                        onChange={(event) => setPromptPackState({
                          ...promptPackState,
                          scene_prompts: { ...promptPackState.scene_prompts, action: event.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="prompt-environment">环境 Prompt</Label>
                      <Textarea
                        id="prompt-environment"
                        aria-label="环境 Prompt"
                        value={promptPackState.scene_prompts.environment}
                        onChange={(event) => setPromptPackState({
                          ...promptPackState,
                          scene_prompts: { ...promptPackState.scene_prompts, environment: event.target.value },
                        })}
                      />
                    </div>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="prompt-hard-constraints">硬约束</Label>
                    <Textarea
                      id="prompt-hard-constraints"
                      aria-label="硬约束"
                      value={listToLines(promptPackState.hard_constraints)}
                      onChange={(event) => setPromptPackState({ ...promptPackState, hard_constraints: linesToList(event.target.value) })}
                    />
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="grid gap-2">
                      <Label htmlFor="prompt-tone">语气控制</Label>
                      <Input
                        id="prompt-tone"
                        aria-label="语气控制"
                        value={promptPackState.style_controls.tone}
                        onChange={(event) => setPromptPackState({
                          ...promptPackState,
                          style_controls: { ...promptPackState.style_controls, tone: event.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="prompt-rhythm">节奏控制</Label>
                      <Input
                        id="prompt-rhythm"
                        aria-label="节奏控制"
                        value={promptPackState.style_controls.rhythm}
                        onChange={(event) => setPromptPackState({
                          ...promptPackState,
                          style_controls: { ...promptPackState.style_controls, rhythm: event.target.value },
                        })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="prompt-anchor">证据锚点</Label>
                      <Input
                        id="prompt-anchor"
                        aria-label="证据锚点"
                        value={promptPackState.style_controls.evidence_anchor}
                        onChange={(event) => setPromptPackState({
                          ...promptPackState,
                          style_controls: { ...promptPackState.style_controls, evidence_anchor: event.target.value },
                        })}
                      />
                    </div>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="prompt-few-shot-slots">Few-shot 槽位</Label>
                    <Textarea
                      id="prompt-few-shot-slots"
                      aria-label="Few-shot 槽位"
                      className="min-h-[120px]"
                      value={fewShotSlotsToLines(promptPackState.few_shot_slots)}
                      onChange={(event) => setPromptPackState({ ...promptPackState, few_shot_slots: linesToFewShotSlots(event.target.value) })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="prompt-mount-project">挂载到项目</Label>
                    <Select
                      value={mountProjectId ?? NONE_VALUE}
                      onValueChange={(value) => setMountProjectId(value === NONE_VALUE ? null : value)}
                    >
                      <SelectTrigger id="prompt-mount-project" aria-label="挂载到项目" className="bg-background">
                        <SelectValue placeholder="仅保存为全局风格资产" />
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
                  <div className="flex justify-end">
                    <Button
                      type="button"
                      onClick={() => saveProfileMutation.mutate()}
                      disabled={saveProfileMutation.isPending}
                    >
                      保存结果
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
