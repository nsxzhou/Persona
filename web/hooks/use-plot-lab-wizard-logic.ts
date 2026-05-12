import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { useForm, type UseFormReturn } from "react-hook-form";

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
import { useAnalysisJobLogsQuery } from "@/hooks/use-analysis-job-logs";
import {
  isAnalysisJobProcessingStatus,
  makeAnalysisArtifactResource,
  mergeAnalysisStatusIntoJob,
  useAnalysisJobCommandMutation,
  useAnalysisJobQueries,
  useAnalysisProfileSaveMutation,
  useRefreshAnalysisJobDetailWhenSucceeded,
} from "@/hooks/use-analysis-wizard-primitives";

type WizardStep = 1 | 2 | 3;

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

const IMMUTABLE_ARTIFACT_QUERY = {
  staleTime: Infinity,
  gcTime: 30 * 60 * 1000,
} as const;

export function isProcessingStatus(status: PlotAnalysisJob["status"] | undefined) {
  return isAnalysisJobProcessingStatus(status);
}

export function usePlotLabJobLogsQuery(jobId: string, isProcessing: boolean) {
  return useAnalysisJobLogsQuery<PlotAnalysisJobLogs>({
    jobId,
    isProcessing,
    queryKey: plotLabQueryKeys.jobs.logs(jobId),
    queryFn: (offset) => api.getPlotAnalysisJobLogs(jobId, offset),
    refetchOnWindowFocus: false,
    staleTime: 1000,
  });
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
  const useExistingProfileQuery = Boolean(job?.plot_profile_id);

  return {
    existingProfile,
    reportResource: makeAnalysisArtifactResource<string>({
      value: report,
      artifactQuery: reportQuery,
      existingProfileQuery,
      useExistingProfileQuery,
    }),
    skeletonResource: makeAnalysisArtifactResource<string>({
      value: skeleton,
      artifactQuery: skeletonQuery,
      existingProfileQuery,
      useExistingProfileQuery,
    }),
    storyEngineResource: makeAnalysisArtifactResource<string>({
      value: storyEngine,
      artifactQuery: storyEngineQuery,
      existingProfileQuery,
      useExistingProfileQuery,
    }),
  };
}

function usePlotLabJobDetail(jobId: string) {
  const { statusQuery, jobQuery } = useAnalysisJobQueries<
    PlotAnalysisJob,
    PlotAnalysisJobStatusSnapshot
  >({
    statusQueryKey: plotLabQueryKeys.jobs.status(jobId),
    statusQueryFn: () => api.getPlotAnalysisJobStatus(jobId),
    detailQueryKey: plotLabQueryKeys.jobs.detail(jobId),
    detailQueryFn: () => api.getPlotAnalysisJob(jobId),
    isProcessingStatus,
  });

  useRefreshAnalysisJobDetailWhenSucceeded({
    status: statusQuery.data?.status,
    detailStatus: jobQuery.data?.status,
    isDetailFetching: jobQuery.isFetching,
    refetchDetail: jobQuery.refetch,
    oncePerCompletion: true,
  });

  const job = mergeAnalysisStatusIntoJob(jobQuery.data ?? null, statusQuery.data ?? null);
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
  return useAnalysisProfileSaveMutation({
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
    successMessage: "情节档案已保存",
    onSuccessCallback,
    editProfileQueryKey: profileQueryKeys.plot.detail(job?.plot_profile_id),
    editJobQueryKey: job?.id ? plotLabQueryKeys.jobs.detail(job.id) : undefined,
    saveListsQueryKey: plotLabQueryKeys.jobs.lists(),
    redirectPath: "/plot-lab",
  });
}

function useResumePlotAnalysisJobMutation(jobId: string) {
  return useAnalysisJobCommandMutation({
    jobId,
    mutationFn: api.resumePlotAnalysisJob,
    successMessage: "任务已恢复",
    detailQueryKey: plotLabQueryKeys.jobs.detail(jobId),
    listsQueryKey: plotLabQueryKeys.jobs.lists(),
  });
}

function usePausePlotAnalysisJobMutation(jobId: string) {
  return useAnalysisJobCommandMutation({
    jobId,
    mutationFn: api.pausePlotAnalysisJob,
    successMessage: "已发送暂停请求",
    detailQueryKey: plotLabQueryKeys.jobs.detail(jobId),
    listsQueryKey: plotLabQueryKeys.jobs.lists(),
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
