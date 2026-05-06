import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { profileQueryKeys } from "@/lib/profile-query-keys";
import { plotLabQueryKeys } from "@/lib/plot-lab-query-keys";
import { formSchema, makeEmptyFormValues, type FormValues } from "@/lib/validations/plot-lab";
import {
  type PlotAnalysisJobLogs,
  type PlotAnalysisJob,
  type PlotAnalysisJobStage,
  type PlotProfile,
  type PlotAnalysisJobStatusSnapshot,
} from "@/lib/types";

type WizardStep = 1 | 2 | 3;

import { makeDetailResource } from "@/lib/wizard-utils";

export const PLOT_STAGE_LABELS: Record<PlotAnalysisJobStage, string> = {
  preparing_input: "正在准备输入",
  building_skeleton: "正在构建全书骨架",
  selecting_focus_chunks: "正在选择重点章节",
  analyzing_focus_chunks: "正在分析重点章节",
  aggregating: "正在聚合结果",
  reporting: "正在生成报告",
  postprocessing: "正在生成 Plot Writing Guide",
};

export function formatPlotStageLabel(
  stage: PlotAnalysisJobStage | string | null | undefined,
): string {
  if (!stage) return "初始化";
  return PLOT_STAGE_LABELS[stage as PlotAnalysisJobStage] ?? stage;
}

const LOG_WINDOW_SIZE = 64 * 1024;
const IMMUTABLE_ARTIFACT_QUERY = {
  staleTime: Infinity,
  gcTime: 30 * 60 * 1000,
} as const;

export function isProcessingStatus(status: PlotAnalysisJob["status"] | undefined) {
  return status === "pending" || status === "running";
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
  const offsetRef = React.useRef(0);
  const [logs, setLogs] = React.useState("");

  React.useEffect(() => {
    offsetRef.current = 0;
    setLogs("");
  }, [jobId]);

  const query = useQuery<PlotAnalysisJobLogs>({
    queryKey: plotLabQueryKeys.jobs.logs(jobId),
    queryFn: () => api.getPlotAnalysisJobLogs(jobId, offsetRef.current),
    refetchInterval: isProcessing ? 1000 : false,
    refetchOnWindowFocus: false,
    staleTime: 1000,
  });

  React.useEffect(() => {
    const payload = query.data as PlotAnalysisJobLogs | undefined;
    if (!payload) return;
    setLogs((prev) => {
      const next = payload.truncated ? payload.content : prev + payload.content;
      return next.slice(-LOG_WINDOW_SIZE);
    });
    offsetRef.current = payload.next_offset;
  }, [query.data]);

  return {
    ...query,
    logs,
  };
}

function usePlotLabResourcesQueries(jobId: string, job: PlotAnalysisJob | null) {
  const existingProfileQuery = useQuery({
    queryKey: profileQueryKeys.plot.detail(job?.plot_profile_id),
    queryFn: () => api.getPlotProfile(String(job?.plot_profile_id)),
    enabled: Boolean(job?.plot_profile_id),
  });

  const isCompletedAndNoProfile = Boolean(job && job.status === "succeeded" && !job.plot_profile_id);
  const needsReport = isCompletedAndNoProfile;
  const needsSkeleton = isCompletedAndNoProfile;
  const needsStoryEngine = isCompletedAndNoProfile;

  const reportQuery = useQuery({
    queryKey: plotLabQueryKeys.jobs.analysisReport(jobId),
    queryFn: () => api.getPlotAnalysisJobAnalysisReport(jobId),
    enabled: needsReport,
    ...IMMUTABLE_ARTIFACT_QUERY,
  });

  const skeletonQuery = useQuery({
    queryKey: plotLabQueryKeys.jobs.plotSkeleton(jobId),
    queryFn: () => api.getPlotAnalysisJobPlotSkeleton(jobId),
    enabled: needsSkeleton,
    ...IMMUTABLE_ARTIFACT_QUERY,
  });

  const storyEngineQuery = useQuery({
    queryKey: plotLabQueryKeys.jobs.storyEngine(jobId),
    queryFn: () => api.getPlotAnalysisJobStoryEngine(jobId),
    enabled: needsStoryEngine,
    ...IMMUTABLE_ARTIFACT_QUERY,
  });

  return { existingProfileQuery, reportQuery, skeletonQuery, storyEngineQuery };
}

function mergeJobResources(
  job: PlotAnalysisJob | null,
  queries: ReturnType<typeof usePlotLabResourcesQueries>
) {
  const { existingProfileQuery, reportQuery, skeletonQuery, storyEngineQuery } = queries;
  const existingProfile = existingProfileQuery.data ?? null;

  const report = existingProfile?.analysis_report_markdown ?? reportQuery.data ?? null;
  const skeleton = existingProfile?.plot_skeleton_markdown ?? skeletonQuery.data ?? null;
  const storyEngine = existingProfile?.story_engine_markdown ?? storyEngineQuery.data ?? null;

  const makeRes = (val: string | null, q: ReturnType<typeof useQuery>) => makeDetailResource<string>(val, {
    isLoading: val == null ? (job?.plot_profile_id ? existingProfileQuery.isLoading : q.isLoading) : false,
    isError: val == null ? (job?.plot_profile_id ? existingProfileQuery.isError : q.isError) : false,
    error: val == null ? ((job?.plot_profile_id ? existingProfileQuery.error : q.error) as Error | null) : null,
  });

  return {
    existingProfile,
    reportResource: makeRes(report, reportQuery),
    skeletonResource: makeRes(skeleton, skeletonQuery),
    storyEngineResource: makeRes(storyEngine, storyEngineQuery),
  };
}

function usePlotLabJobDetail(jobId: string) {
  const statusQuery = usePlotLabJobStatusQuery(jobId);
  const jobQuery = usePlotLabJobDetailQuery(jobId);
  const hasRequestedFinalDetailRef = React.useRef(false);

  React.useEffect(() => {
    if (statusQuery.data?.status !== "succeeded") {
      hasRequestedFinalDetailRef.current = false;
      return;
    }
    if (
      statusQuery.data?.status === "succeeded" &&
      jobQuery.data?.status !== "succeeded" &&
      !jobQuery.isFetching &&
      !hasRequestedFinalDetailRef.current
    ) {
      hasRequestedFinalDetailRef.current = true;
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

function usePlotLabWizardState({
  jobId,
  job,
  existingProfile,
  skeletonMarkdown,
  storyEngineMarkdown,
}: {
  jobId: string;
  job: PlotAnalysisJob | null;
  existingProfile: PlotProfile | null;
  skeletonMarkdown: string | null;
  storyEngineMarkdown: string | null;
}) {
  const [step, setStep] = React.useState<WizardStep>(1);
  const initializedJobId = React.useRef<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema, undefined, { mode: "sync" }),
    defaultValues: makeEmptyFormValues(),
  });

  React.useEffect(() => {
    initializedJobId.current = null;
    setStep(1);
    form.reset(makeEmptyFormValues());
  }, [jobId, form]);

  React.useEffect(() => {
    if (initializedJobId.current === jobId) return;

    if (existingProfile) {
      form.reset({
        plotName: existingProfile.plot_name,
        plotSkeletonMarkdown: existingProfile.plot_skeleton_markdown ?? "",
        storyEngineMarkdown: existingProfile.story_engine_markdown,
      });
      initializedJobId.current = jobId;
      return;
    }

    if (job?.status === "succeeded" && skeletonMarkdown && storyEngineMarkdown) {
      form.reset({
        plotName: job.plot_name,
        plotSkeletonMarkdown: skeletonMarkdown,
        storyEngineMarkdown,
      });
      initializedJobId.current = jobId;
    }
  }, [existingProfile, form, job, jobId, skeletonMarkdown, storyEngineMarkdown]);

  return {
    step,
    setStep,
    form,
    handleStep3Next: () => setStep(3),
  };
}

function useSavePlotProfileMutation({
  job,
  form,
  onSuccessCallback,
}: {
  job: PlotAnalysisJob | null;
  form: UseFormReturn<FormValues>;
  onSuccessCallback?: () => void;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const values = form.getValues();
      if (!job) throw new Error("缺少保存数据");

      const payload = {
        plot_name: values.plotName,
        plot_skeleton_markdown: values.plotSkeletonMarkdown,
        story_engine_markdown: values.storyEngineMarkdown,
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
        void queryClient.invalidateQueries({ queryKey: profileQueryKeys.plot.detail(job?.plot_profile_id) });
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

function usePlotLabWizardMutations(
  jobId: string,
  {
    job,
    form,
    isEditing,
    setIsEditing,
  }: {
    job: PlotAnalysisJob | null;
    form: UseFormReturn<FormValues>;
    isEditing: boolean;
    setIsEditing: React.Dispatch<React.SetStateAction<boolean>>;
  },
) {
  const saveProfileMutation = useSavePlotProfileMutation({
    job,
    form,
    onSuccessCallback: isEditing ? () => setIsEditing(false) : undefined,
  });
  const resumeJobMutation = useResumePlotAnalysisJobMutation(jobId);
  const pauseJobMutation = usePausePlotAnalysisJobMutation(jobId);

  return {
    saveProfileMutation,
    resumeJobMutation,
    pauseJobMutation,
    handleSave: () => void saveProfileMutation.mutateAsync(),
    handleResume: () => void resumeJobMutation.mutateAsync(),
    handlePause: () => void pauseJobMutation.mutateAsync(),
  };
}

export function usePlotLabWizardLogic(jobId: string) {
  const [isEditing, setIsEditing] = React.useState(false);
  const detail = usePlotLabJobDetail(jobId);
  const wizardState = usePlotLabWizardState({
    jobId,
    job: detail.job,
    existingProfile: detail.existingProfile,
    skeletonMarkdown: detail.skeletonResource.data,
    storyEngineMarkdown: detail.storyEngineResource.data,
  });
  const mutations = usePlotLabWizardMutations(jobId, {
    job: detail.job,
    form: wizardState.form,
    isEditing,
    setIsEditing,
  });

  return {
    ...wizardState,
    isEditing,
    setIsEditing,
    job: detail.job,
    existingProfile: detail.existingProfile,
    reportResource: detail.reportResource,
    skeletonResource: detail.skeletonResource,
    storyEngineResource: detail.storyEngineResource,
    saveProfileMutation: mutations.saveProfileMutation,
    resumeJobMutation: mutations.resumeJobMutation,
    pauseJobMutation: mutations.pauseJobMutation,
    handleSave: mutations.handleSave,
    handleResume: mutations.handleResume,
    handlePause: mutations.handlePause,
    isLoading: detail.isLoading,
    errorState: detail.errorState,
  };
}
