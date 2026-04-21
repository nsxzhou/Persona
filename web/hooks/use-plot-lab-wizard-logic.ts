import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { plotLabQueryKeys } from "@/lib/plot-lab-query-keys";
import { formSchema, makeEmptyFormValues, type FormValues } from "@/lib/validations/plot-lab";
import {
  type PlotAnalysisJobLogs,
  type PlotAnalysisJob,
  type PlotAnalysisJobStage,
  type PlotProfile,
  type PlotAnalysisJobStatusSnapshot,
} from "@/lib/types";

type WizardStep = 1 | 2 | 3 | 4;

export const PLOT_STAGE_LABELS: Record<PlotAnalysisJobStage, string> = {
  preparing_input: "正在准备输入",
  building_skeleton: "正在构建全书骨架",
  analyzing_chunks: "正在分析章节",
  aggregating: "正在聚合结果",
  reporting: "正在生成报告",
  summarizing: "正在生成摘要",
  composing_prompt_pack: "正在组装 Prompt Pack",
};

export function formatPlotStageLabel(
  stage: PlotAnalysisJobStage | string | null | undefined,
): string {
  if (!stage) return "初始化";
  return PLOT_STAGE_LABELS[stage as PlotAnalysisJobStage] ?? stage;
}

type DetailResource<T> = {
  data: T | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
};

type DetailQueryLike = {
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
};

const LOG_WINDOW_SIZE = 64 * 1024;

export function isProcessingStatus(status: PlotAnalysisJob["status"] | undefined) {
  return status === "pending" || status === "running";
}

function makeDetailResource<T>(
  data: T | null | undefined,
  query: DetailQueryLike,
): DetailResource<T> {
  return {
    data: data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
  };
}

function mergeStatusIntoJob(
  job: PlotAnalysisJob | null,
  statusSnapshot: PlotAnalysisJobStatusSnapshot | null,
) {
  if (!job || !statusSnapshot) return job;
  return {
    ...job,
    status: statusSnapshot.status,
    stage: statusSnapshot.stage,
    error_message: statusSnapshot.error_message,
    updated_at: statusSnapshot.updated_at,
  };
}

function usePlotLabJobStatusQuery(jobId: string) {
  return useQuery({
    queryKey: plotLabQueryKeys.jobs.status(jobId),
    queryFn: () => api.getPlotAnalysisJobStatus(jobId),
    refetchInterval: (query) => (isProcessingStatus(query.state.data?.status) ? 2000 : false),
  });
}

function usePlotLabJobDetailQuery(jobId: string) {
  return useQuery({
    queryKey: plotLabQueryKeys.jobs.detail(jobId),
    queryFn: () => api.getPlotAnalysisJob(jobId),
  });
}

export function usePlotLabJobLogsQuery(jobId: string, isProcessing: boolean) {
  const [offset, setOffset] = React.useState(0);
  const [logs, setLogs] = React.useState("");

  React.useEffect(() => {
    setOffset(0);
    setLogs("");
  }, [jobId]);

  const query = useQuery<PlotAnalysisJobLogs>({
    queryKey: plotLabQueryKeys.jobs.logs(jobId),
    queryFn: () => api.getPlotAnalysisJobLogs(jobId, offset),
    refetchInterval: isProcessing ? 1000 : false,
  });

  React.useEffect(() => {
    const payload = query.data as PlotAnalysisJobLogs | undefined;
    if (!payload) return;
    setLogs((prev) => {
      const next = payload.truncated ? payload.content : prev + payload.content;
      return next.slice(-LOG_WINDOW_SIZE);
    });
    setOffset((prev) => (prev === payload.next_offset ? prev : payload.next_offset));
  }, [query.data]);

  return {
    ...query,
    logs,
  };
}

function usePlotLabResourcesQueries(jobId: string, job: PlotAnalysisJob | null) {
  const existingProfileQuery = useQuery({
    queryKey: ["plot-profiles", job?.plot_profile_id],
    queryFn: () => api.getPlotProfile(String(job?.plot_profile_id)),
    enabled: Boolean(job?.plot_profile_id),
  });

  const isCompletedAndNoProfile = Boolean(job && job.status === "succeeded" && !job.plot_profile_id);
  const needsReport = isCompletedAndNoProfile;
  const needsSummary = isCompletedAndNoProfile;
  const needsSkeleton = isCompletedAndNoProfile;
  const needsPromptPack = isCompletedAndNoProfile;

  const reportQuery = useQuery({
    queryKey: plotLabQueryKeys.jobs.analysisReport(jobId),
    queryFn: () => api.getPlotAnalysisJobAnalysisReport(jobId),
    enabled: needsReport,
  });

  const summaryQuery = useQuery({
    queryKey: plotLabQueryKeys.jobs.plotSummary(jobId),
    queryFn: () => api.getPlotAnalysisJobPlotSummary(jobId),
    enabled: needsSummary,
  });

  const skeletonQuery = useQuery({
    queryKey: plotLabQueryKeys.jobs.plotSkeleton(jobId),
    queryFn: () => api.getPlotAnalysisJobPlotSkeleton(jobId),
    enabled: needsSkeleton,
  });

  const promptPackQuery = useQuery({
    queryKey: plotLabQueryKeys.jobs.promptPack(jobId),
    queryFn: () => api.getPlotAnalysisJobPromptPack(jobId),
    enabled: needsPromptPack,
  });

  return { existingProfileQuery, reportQuery, summaryQuery, skeletonQuery, promptPackQuery };
}

function mergeJobResources(
  job: PlotAnalysisJob | null,
  queries: ReturnType<typeof usePlotLabResourcesQueries>
) {
  const { existingProfileQuery, reportQuery, summaryQuery, skeletonQuery, promptPackQuery } = queries;
  const existingProfile = existingProfileQuery.data ?? null;

  const report = existingProfile?.analysis_report_markdown ?? reportQuery.data ?? null;
  const summary = existingProfile?.plot_summary_markdown ?? summaryQuery.data ?? null;
  const skeleton = existingProfile?.plot_skeleton_markdown ?? skeletonQuery.data ?? null;
  const promptPack = existingProfile?.prompt_pack_markdown ?? promptPackQuery.data ?? null;

  const makeRes = (val: string | null, q: ReturnType<typeof useQuery>) => makeDetailResource<string>(val, {
    isLoading: val == null ? (job?.plot_profile_id ? existingProfileQuery.isLoading : q.isLoading) : false,
    isError: val == null ? (job?.plot_profile_id ? existingProfileQuery.isError : q.isError) : false,
    error: val == null ? ((job?.plot_profile_id ? existingProfileQuery.error : q.error) as Error | null) : null,
  });

  return {
    existingProfile,
    reportResource: makeRes(report, reportQuery),
    summaryResource: makeRes(summary, summaryQuery),
    skeletonResource: makeRes(skeleton, skeletonQuery),
    promptPackResource: makeRes(promptPack, promptPackQuery),
  };
}

function usePlotLabJobDetail(jobId: string) {
  const statusQuery = usePlotLabJobStatusQuery(jobId);
  const jobQuery = usePlotLabJobDetailQuery(jobId);

  React.useEffect(() => {
    if (
      statusQuery.data?.status === "succeeded" &&
      jobQuery.data?.status !== "succeeded" &&
      !jobQuery.isFetching
    ) {
      void jobQuery.refetch();
    }
  }, [jobQuery.data?.status, jobQuery.isFetching, jobQuery.refetch, statusQuery.data?.status]);

  const job = mergeStatusIntoJob(jobQuery.data ?? null, statusQuery.data ?? null);
  const resourcesQueries = usePlotLabResourcesQueries(jobId, job);
  const resources = mergeJobResources(job, resourcesQueries);

  let errorState: { title: string; message: string } | null = null;
  if (jobQuery.isError || (statusQuery.isError && !jobQuery.data) || resourcesQueries.existingProfileQuery.isError) {
    const queryError = resourcesQueries.existingProfileQuery.error ?? jobQuery.error ?? statusQuery.error;
    errorState = {
      title: "加载任务失败",
      message: queryError instanceof Error ? queryError.message : "请重试",
    };
  } else if (!jobQuery.isLoading && !job) {
    errorState = { title: "任务不存在", message: "未找到对应的情节分析任务" };
  }

  return {
    job,
    ...resources,
    isLoading: jobQuery.isLoading && !jobQuery.data,
    errorState,
  };
}

function useMountableProjects(enabled: boolean) {
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.getProjects({ includeArchived: false, limit: 100 }),
    enabled,
  });

  return {
    projects: projectsQuery.data ?? [],
    isLoading: projectsQuery.isLoading,
  };
}

function usePlotLabWizardState({
  jobId,
  job,
  existingProfile,
  summaryMarkdown,
  promptPackMarkdown,
}: {
  jobId: string;
  job: PlotAnalysisJob | null;
  existingProfile: PlotProfile | null;
  summaryMarkdown: string | null;
  promptPackMarkdown: string | null;
}) {
  const [step, setStep] = React.useState<WizardStep>(1);
  const [mountProjectId, setMountProjectId] = React.useState<string | null>(null);
  const initializedJobId = React.useRef<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema, undefined, { mode: "sync" }),
    defaultValues: makeEmptyFormValues(),
  });

  React.useEffect(() => {
    initializedJobId.current = null;
    setStep(1);
    setMountProjectId(null);
    form.reset(makeEmptyFormValues());
  }, [jobId, form]);

  React.useEffect(() => {
    if (initializedJobId.current === jobId) return;

    if (existingProfile) {
      form.reset({
        plotName: existingProfile.plot_name,
        plotSummaryMarkdown: existingProfile.plot_summary_markdown,
        promptPackMarkdown: existingProfile.prompt_pack_markdown,
      });
      initializedJobId.current = jobId;
      return;
    }

    if (job?.status === "succeeded" && summaryMarkdown && promptPackMarkdown) {
      form.reset({
        plotName: job.plot_name,
        plotSummaryMarkdown: summaryMarkdown,
        promptPackMarkdown,
      });
      initializedJobId.current = jobId;
    }
  }, [existingProfile, form, job, jobId, promptPackMarkdown, summaryMarkdown]);

  return {
    step,
    setStep,
    mountProjectId,
    setMountProjectId,
    form,
    handleStep3Next: () => setStep(4),
  };
}

function useSavePlotProfileMutation({
  job,
  form,
  mountProjectId,
  onSuccessCallback,
}: {
  job: PlotAnalysisJob | null;
  form: UseFormReturn<FormValues>;
  mountProjectId: string | null;
  onSuccessCallback?: () => void;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const values = form.getValues();
      if (!job) throw new Error("缺少保存数据");

      const mountPayload = mountProjectId ? { mount_project_id: mountProjectId } : {};
      const payload = {
        ...mountPayload,
        plot_name: values.plotName,
        plot_summary_markdown: values.plotSummaryMarkdown,
        prompt_pack_markdown: values.promptPackMarkdown,
      };

      if (job.plot_profile_id) {
        return api.updatePlotProfile(job.plot_profile_id, payload);
      }

      return api.createPlotProfile({
        ...payload,
        job_id: job.id,
      });
    },
    onSuccess: () => {
      toast.success("情节档案已保存");
      if (onSuccessCallback) {
        onSuccessCallback();
        void queryClient.invalidateQueries({ queryKey: ["plot-profiles", job?.plot_profile_id] });
        if (job?.id) {
          void queryClient.invalidateQueries({ queryKey: plotLabQueryKeys.jobs.detail(job.id) });
        }
      } else {
        void queryClient.invalidateQueries({ queryKey: plotLabQueryKeys.jobs.lists() });
        router.push("/plot-lab");
      }
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "未知错误");
    },
  });
}

function useResumePlotAnalysisJobMutation(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.resumePlotAnalysisJob(jobId),
    onSuccess: () => {
      toast.success("任务已恢复");
      void queryClient.invalidateQueries({ queryKey: plotLabQueryKeys.jobs.detail(jobId) });
      void queryClient.invalidateQueries({ queryKey: plotLabQueryKeys.jobs.lists() });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "未知错误");
    },
  });
}

function usePausePlotAnalysisJobMutation(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.pausePlotAnalysisJob(jobId),
    onSuccess: () => {
      toast.success("已发送暂停请求");
      void queryClient.invalidateQueries({ queryKey: plotLabQueryKeys.jobs.detail(jobId) });
      void queryClient.invalidateQueries({ queryKey: plotLabQueryKeys.jobs.lists() });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "未知错误");
    },
  });
}

export function usePlotLabWizardLogic(jobId: string) {
  const [isEditing, setIsEditing] = React.useState(false);
  const detail = usePlotLabJobDetail(jobId);
  const wizardState = usePlotLabWizardState({
    jobId,
    job: detail.job,
    existingProfile: detail.existingProfile,
    summaryMarkdown: detail.summaryResource.data,
    promptPackMarkdown: detail.promptPackResource.data,
  });
  const shouldLoadProjects = wizardState.step === 4 && !detail.existingProfile;
  const { projects } = useMountableProjects(shouldLoadProjects);
  const saveProfileMutation = useSavePlotProfileMutation({
    job: detail.job,
    form: wizardState.form,
    mountProjectId: wizardState.mountProjectId,
    onSuccessCallback: isEditing ? () => setIsEditing(false) : undefined,
  });
  const resumeJobMutation = useResumePlotAnalysisJobMutation(jobId);
  const pauseJobMutation = usePausePlotAnalysisJobMutation(jobId);

  return {
    ...wizardState,
    isEditing,
    setIsEditing,
    job: detail.job,
    existingProfile: detail.existingProfile,
    reportResource: detail.reportResource,
    summaryResource: detail.summaryResource,
    skeletonResource: detail.skeletonResource,
    promptPackResource: detail.promptPackResource,
    projects,
    saveProfileMutation,
    resumeJobMutation,
    pauseJobMutation,
    handleSave: () => void saveProfileMutation.mutateAsync(),
    handleResume: () => void resumeJobMutation.mutateAsync(),
    handlePause: () => void pauseJobMutation.mutateAsync(),
    isLoading: detail.isLoading,
    errorState: detail.errorState,
  };
}
