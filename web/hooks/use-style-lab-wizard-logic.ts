import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { styleLabQueryKeys } from "@/lib/style-lab-query-keys";
import { formSchema, makeEmptyFormValues, type FormValues } from "@/lib/validations/style-lab";
import {
  type StyleAnalysisJobLogs,
  type StyleAnalysisJob,
  type StyleProfile,
  type StyleAnalysisJobStatusSnapshot,
} from "@/lib/types";

type WizardStep = 1 | 2 | 3;

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

export function isProcessingStatus(status: StyleAnalysisJob["status"] | undefined) {
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
  job: StyleAnalysisJob | null,
  statusSnapshot: StyleAnalysisJobStatusSnapshot | null,
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

function useStyleLabJobStatusQuery(jobId: string) {
  return useQuery({
    queryKey: styleLabQueryKeys.jobs.status(jobId),
    queryFn: () => api.getStyleAnalysisJobStatus(jobId),
    refetchInterval: (query) => (isProcessingStatus(query.state.data?.status) ? 2000 : false),
  });
}

function useStyleLabJobDetailQuery(jobId: string) {
  return useQuery({
    queryKey: styleLabQueryKeys.jobs.detail(jobId),
    queryFn: () => api.getStyleAnalysisJob(jobId),
  });
}

export function useStyleLabJobLogsQuery(jobId: string, isProcessing: boolean) {
  const [offset, setOffset] = React.useState(0);
  const [logs, setLogs] = React.useState("");

  React.useEffect(() => {
    setOffset(0);
    setLogs("");
  }, [jobId]);

  const query = useQuery<StyleAnalysisJobLogs>({
    queryKey: styleLabQueryKeys.jobs.logs(jobId),
    queryFn: () => api.getStyleAnalysisJobLogs(jobId, offset),
    refetchInterval: isProcessing ? 1000 : false,
  });

  React.useEffect(() => {
    const payload = query.data as StyleAnalysisJobLogs | undefined;
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

function useStyleLabResourcesQueries(jobId: string, job: StyleAnalysisJob | null) {
  const existingProfileQuery = useQuery({
    queryKey: ["style-profiles", job?.style_profile_id],
    queryFn: () => api.getStyleProfile(String(job?.style_profile_id)),
    enabled: Boolean(job?.style_profile_id),
  });

  const isCompletedAndNoProfile = Boolean(job && job.status === "succeeded" && !job.style_profile_id);
  const needsReport = isCompletedAndNoProfile;
  const needsSummary = isCompletedAndNoProfile;
  const needsPromptPack = isCompletedAndNoProfile;

  const reportQuery = useQuery({
    queryKey: styleLabQueryKeys.jobs.analysisReport(jobId),
    queryFn: () => api.getStyleAnalysisJobAnalysisReport(jobId),
    enabled: needsReport,
  });
  
  const summaryQuery = useQuery({
    queryKey: styleLabQueryKeys.jobs.styleSummary(jobId),
    queryFn: () => api.getStyleAnalysisJobStyleSummary(jobId),
    enabled: needsSummary,
  });
  
  const promptPackQuery = useQuery({
    queryKey: styleLabQueryKeys.jobs.promptPack(jobId),
    queryFn: () => api.getStyleAnalysisJobPromptPack(jobId),
    enabled: needsPromptPack,
  });

  return { existingProfileQuery, reportQuery, summaryQuery, promptPackQuery };
}

function mergeJobResources(
  job: StyleAnalysisJob | null,
  queries: ReturnType<typeof useStyleLabResourcesQueries>
) {
  const { existingProfileQuery, reportQuery, summaryQuery, promptPackQuery } = queries;
  const existingProfile = existingProfileQuery.data ?? null;

  const report = existingProfile?.analysis_report_markdown ?? reportQuery.data ?? null;
  const summary = existingProfile?.style_summary_markdown ?? summaryQuery.data ?? null;
  const promptPack = existingProfile?.prompt_pack_markdown ?? promptPackQuery.data ?? null;

  const makeRes = (val: string | null, q: ReturnType<typeof useQuery>) => makeDetailResource<string>(val, {
    isLoading: val == null ? (job?.style_profile_id ? existingProfileQuery.isLoading : q.isLoading) : false,
    isError: val == null ? (job?.style_profile_id ? existingProfileQuery.isError : q.isError) : false,
    error: val == null ? ((job?.style_profile_id ? existingProfileQuery.error : q.error) as Error | null) : null,
  });

  return {
    existingProfile,
    reportResource: makeRes(report, reportQuery),
    summaryResource: makeRes(summary, summaryQuery),
    promptPackResource: makeRes(promptPack, promptPackQuery),
  };
}

function useStyleLabJobDetail(jobId: string) {
  const statusQuery = useStyleLabJobStatusQuery(jobId);
  const jobQuery = useStyleLabJobDetailQuery(jobId);

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
  const resourcesQueries = useStyleLabResourcesQueries(jobId, job);
  const resources = mergeJobResources(job, resourcesQueries);

  let errorState: { title: string; message: string } | null = null;
  if (jobQuery.isError || (statusQuery.isError && !jobQuery.data) || resourcesQueries.existingProfileQuery.isError) {
    const queryError = resourcesQueries.existingProfileQuery.error ?? jobQuery.error ?? statusQuery.error;
    errorState = {
      title: "加载任务失败",
      message: queryError instanceof Error ? queryError.message : "请重试",
    };
  } else if (!jobQuery.isLoading && !job) {
    errorState = { title: "任务不存在", message: "未找到对应的风格分析任务" };
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

function useStyleLabWizardState({
  jobId,
  job,
  existingProfile,
  summaryMarkdown,
  promptPackMarkdown,
}: {
  jobId: string;
  job: StyleAnalysisJob | null;
  existingProfile: StyleProfile | null;
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
        styleName: existingProfile.style_name,
        styleSummaryMarkdown: existingProfile.style_summary_markdown,
        promptPackMarkdown: existingProfile.prompt_pack_markdown,
      });
      initializedJobId.current = jobId;
      return;
    }

    if (job?.status === "succeeded" && summaryMarkdown && promptPackMarkdown) {
      form.reset({
        styleName: job.style_name,
        styleSummaryMarkdown: summaryMarkdown,
        promptPackMarkdown: promptPackMarkdown,
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
    handleStep2Next: () => setStep(3),
  };
}

function useSaveStyleProfileMutation({
  job,
  form,
  mountProjectId,
  onSuccessCallback,
}: {
  job: StyleAnalysisJob | null;
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
        style_name: values.styleName,
        style_summary_markdown: values.styleSummaryMarkdown,
        prompt_pack_markdown: values.promptPackMarkdown,
      };

      if (job.style_profile_id) {
        return api.updateStyleProfile(job.style_profile_id, payload);
      }

      return api.createStyleProfile({
        ...payload,
        job_id: job.id,
      });
    },
    onSuccess: () => {
      toast.success("风格档案已保存");
      if (onSuccessCallback) {
        onSuccessCallback();
        void queryClient.invalidateQueries({ queryKey: ["style-profiles", job?.style_profile_id] });
        if (job?.id) {
          void queryClient.invalidateQueries({ queryKey: styleLabQueryKeys.jobs.detail(job.id) });
        }
      } else {
        router.push("/style-lab");
      }
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "未知错误");
    },
  });
}

function useResumeStyleAnalysisJobMutation(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.resumeStyleAnalysisJob(jobId),
    onSuccess: () => {
      toast.success("任务已恢复");
      void queryClient.invalidateQueries({ queryKey: styleLabQueryKeys.jobs.detail(jobId) });
      void queryClient.invalidateQueries({ queryKey: styleLabQueryKeys.jobs.lists() });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "未知错误");
    },
  });
}

function usePauseStyleAnalysisJobMutation(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.pauseStyleAnalysisJob(jobId),
    onSuccess: () => {
      toast.success("已发送暂停请求");
      void queryClient.invalidateQueries({ queryKey: styleLabQueryKeys.jobs.detail(jobId) });
      void queryClient.invalidateQueries({ queryKey: styleLabQueryKeys.jobs.lists() });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "未知错误");
    },
  });
}

export function useStyleLabWizardLogic(jobId: string) {
  const [isEditing, setIsEditing] = React.useState(false);
  const detail = useStyleLabJobDetail(jobId);
  const wizardState = useStyleLabWizardState({
    jobId,
    job: detail.job,
    existingProfile: detail.existingProfile,
    summaryMarkdown: detail.summaryResource.data,
    promptPackMarkdown: detail.promptPackResource.data,
  });
  const shouldLoadProjects = wizardState.step === 3 && !detail.existingProfile;
  const { projects } = useMountableProjects(shouldLoadProjects);
  const saveProfileMutation = useSaveStyleProfileMutation({
    job: detail.job,
    form: wizardState.form,
    mountProjectId: wizardState.mountProjectId,
    onSuccessCallback: isEditing ? () => setIsEditing(false) : undefined,
  });
  const resumeJobMutation = useResumeStyleAnalysisJobMutation(jobId);
  const pauseJobMutation = usePauseStyleAnalysisJobMutation(jobId);

  return {
    ...wizardState,
    isEditing,
    setIsEditing,
    job: detail.job,
    existingProfile: detail.existingProfile,
    reportResource: detail.reportResource,
    summaryResource: detail.summaryResource,
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
