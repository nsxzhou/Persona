import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { formSchema, makeEmptyFormValues, type FormValues } from "@/lib/validations/style-lab";
import {
  type StyleAnalysisJobLogs,
  type StyleAnalysisJob,
  type StyleProfile,
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

type StyleAnalysisJobStatusSnapshot = Pick<
  StyleAnalysisJob,
  "id" | "status" | "stage" | "error_message" | "updated_at"
>;

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
    queryKey: ["style-analysis-jobs", jobId, "status"],
    queryFn: () => api.getStyleAnalysisJobStatus(jobId),
    refetchInterval: (query) => (isProcessingStatus(query.state.data?.status) ? 2000 : false),
  });
}

function useStyleLabJobDetailQuery(jobId: string) {
  return useQuery({
    queryKey: ["style-analysis-jobs", jobId],
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
    queryKey: ["style-analysis-jobs", jobId, "logs", offset],
    queryFn: () => api.getStyleAnalysisJobLogs(jobId, offset),
    refetchInterval: isProcessing ? 1000 : false,
    placeholderData: (previous) => previous,
  });

  React.useEffect(() => {
    const payload = query.data as StyleAnalysisJobLogs | undefined;
    if (!payload) return;
    setLogs((prev) => (payload.truncated ? payload.content : prev + payload.content));
    setOffset((prev) => (prev === payload.next_offset ? prev : payload.next_offset));
  }, [query.data]);

  return {
    ...query,
    logs,
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
  const legacyJob = job as
    | (StyleAnalysisJob & {
        style_profile?: StyleProfile | null;
        analysis_report_markdown?: string | null;
        style_summary_markdown?: string | null;
        prompt_pack_markdown?: string | null;
      })
    | null;
  const embeddedProfile = legacyJob?.style_profile ?? null;
  const existingProfileQuery = useQuery({
    queryKey: ["style-profiles", job?.style_profile_id],
    queryFn: () => api.getStyleProfile(String(job?.style_profile_id)),
    enabled: Boolean(job?.style_profile_id),
  });
  const existingProfile = existingProfileQuery.data ?? null;
  const reportQuery = useQuery({
    queryKey: ["style-analysis-jobs", jobId, "analysis-report"],
    queryFn: () => api.getStyleAnalysisJobAnalysisReport(jobId),
    enabled: Boolean(
      job &&
        job.status === "succeeded" &&
        !job.style_profile_id &&
        !("analysis_report_markdown" in job && job.analysis_report_markdown),
    ),
  });
  const summaryQuery = useQuery({
    queryKey: ["style-analysis-jobs", jobId, "style-summary"],
    queryFn: () => api.getStyleAnalysisJobStyleSummary(jobId),
    enabled: Boolean(
      job &&
        job.status === "succeeded" &&
        !job.style_profile_id &&
        !("style_summary_markdown" in job && job.style_summary_markdown),
    ),
  });
  const promptPackQuery = useQuery({
    queryKey: ["style-analysis-jobs", jobId, "prompt-pack"],
    queryFn: () => api.getStyleAnalysisJobPromptPack(jobId),
    enabled: Boolean(
      job &&
        job.status === "succeeded" &&
        !job.style_profile_id &&
        !("prompt_pack_markdown" in job && job.prompt_pack_markdown),
    ),
  });

  const report =
    existingProfile?.analysis_report_markdown ??
    legacyJob?.analysis_report_markdown ??
    reportQuery.data ??
    null;
  const summary =
    existingProfile?.style_summary_markdown ??
    legacyJob?.style_summary_markdown ??
    summaryQuery.data ??
    null;
  const promptPack =
    existingProfile?.prompt_pack_markdown ??
    legacyJob?.prompt_pack_markdown ??
    promptPackQuery.data ??
    null;

  let errorState: { title: string; message: string } | null = null;
  if (jobQuery.isError || (statusQuery.isError && !jobQuery.data) || existingProfileQuery.isError) {
    const queryError = existingProfileQuery.error ?? jobQuery.error ?? statusQuery.error;
    errorState = {
      title: "加载任务失败",
      message: queryError instanceof Error ? queryError.message : "请重试",
    };
  } else if (!jobQuery.isLoading && !job) {
    errorState = { title: "任务不存在", message: "未找到对应的风格分析任务" };
  }

  return {
    job,
    existingProfile,
    reportResource: makeDetailResource<string>(report, {
      isLoading: report == null ? (job?.style_profile_id ? existingProfileQuery.isLoading : reportQuery.isLoading) : false,
      isError: report == null ? (job?.style_profile_id ? existingProfileQuery.isError : reportQuery.isError) : false,
      error: report == null ? ((job?.style_profile_id ? existingProfileQuery.error : reportQuery.error) as Error | null) : null,
    }),
    summaryResource: makeDetailResource<string>(summary, {
      isLoading: summary == null ? (job?.style_profile_id ? existingProfileQuery.isLoading : summaryQuery.isLoading) : false,
      isError: summary == null ? (job?.style_profile_id ? existingProfileQuery.isError : summaryQuery.isError) : false,
      error: summary == null ? ((job?.style_profile_id ? existingProfileQuery.error : summaryQuery.error) as Error | null) : null,
    }),
    promptPackResource: makeDetailResource<string>(promptPack, {
      isLoading: promptPack == null ? (job?.style_profile_id ? existingProfileQuery.isLoading : promptPackQuery.isLoading) : false,
      isError: promptPack == null ? (job?.style_profile_id ? existingProfileQuery.isError : promptPackQuery.isError) : false,
      error: promptPack == null ? ((job?.style_profile_id ? existingProfileQuery.error : promptPackQuery.error) as Error | null) : null,
    }),
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
        void queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs", job?.id] });
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
      void queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs", jobId, "status"] });
      void queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs", jobId] });
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
      void queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs", jobId, "status"] });
      void queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs", jobId] });
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
