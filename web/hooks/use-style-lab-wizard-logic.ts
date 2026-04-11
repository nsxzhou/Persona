import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { toast } from "sonner";

import { api } from "@/lib/api";
import {
  formSchema,
  makeEmptyPromptPack,
  makeEmptyStyleSummary,
  type FormValues,
} from "@/lib/validations/style-lab";
import {
  STYLE_ANALYSIS_JOB_PROCESSING_STATUSES,
  STYLE_ANALYSIS_JOB_STATUS,
  type AnalysisReport,
  type PromptPack,
  type StyleAnalysisJob,
  type StyleProfile,
  type StyleSummary,
} from "@/lib/types";

type WizardStep = 1 | 2 | 3;

type DetailResource<T> = {
  data: T | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
};

type StyleAnalysisJobStatusSnapshot = Pick<
  StyleAnalysisJob,
  "id" | "status" | "stage" | "error_message" | "updated_at"
>;

function isProcessingStatus(status: StyleAnalysisJob["status"] | undefined) {
  return Boolean(
    status && STYLE_ANALYSIS_JOB_PROCESSING_STATUSES.some((value) => value === status),
  );
}

function makeDetailResource<T>(
  data: T | null | undefined,
  jobQuery: ReturnType<typeof useStyleLabJobDetailQuery>,
): DetailResource<T> {
  return {
    data: data ?? null,
    isLoading: jobQuery.isLoading,
    isError: jobQuery.isError,
    error: jobQuery.error instanceof Error ? jobQuery.error : null,
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
    refetchInterval: (query) =>
      isProcessingStatus(query.state.data?.status) ? 2000 : false,
  });
}

function useStyleLabJobDetailQuery(jobId: string) {
  return useQuery({
    queryKey: ["style-analysis-jobs", jobId],
    queryFn: () => api.getStyleAnalysisJob(jobId),
  });
}

function useStyleLabJobDetail(jobId: string) {
  const statusQuery = useStyleLabJobStatusQuery(jobId);
  const jobQuery = useStyleLabJobDetailQuery(jobId);

  React.useEffect(() => {
    if (
      statusQuery.data?.status === STYLE_ANALYSIS_JOB_STATUS.SUCCEEDED &&
      jobQuery.data?.status !== STYLE_ANALYSIS_JOB_STATUS.SUCCEEDED &&
      !jobQuery.isFetching
    ) {
      void jobQuery.refetch();
    }
  }, [
    jobQuery.data?.status,
    jobQuery.isFetching,
    jobQuery.refetch,
    statusQuery.data?.status,
  ]);

  const job = mergeStatusIntoJob(
    jobQuery.data ?? null,
    statusQuery.data ?? null,
  );
  const existingProfile = job?.style_profile ?? null;

  const report = existingProfile?.analysis_report ?? job?.analysis_report ?? null;
  const summary = existingProfile?.style_summary ?? job?.style_summary ?? null;
  const promptPack = existingProfile?.prompt_pack ?? job?.prompt_pack ?? null;

  let errorState: { title: string; message: string } | null = null;
  if (jobQuery.isError || (statusQuery.isError && !jobQuery.data)) {
    const queryError = jobQuery.error ?? statusQuery.error;
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
    reportResource: makeDetailResource<AnalysisReport>(report, jobQuery),
    summaryResource: makeDetailResource<StyleSummary>(summary, jobQuery),
    promptPackResource: makeDetailResource<PromptPack>(promptPack, jobQuery),
    isLoading: jobQuery.isLoading && !jobQuery.data,
    errorState,
  };
}

function useMountableProjects(enabled: boolean) {
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.getProjects(false),
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
  summary,
  promptPack,
}: {
  jobId: string;
  job: StyleAnalysisJob | null;
  existingProfile: StyleProfile | null;
  summary: StyleSummary | null;
  promptPack: PromptPack | null;
}) {
  const [step, setStep] = React.useState<WizardStep>(1);
  const [mountProjectId, setMountProjectId] = React.useState<string | null>(null);
  const initializedJobId = React.useRef<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema, undefined, { mode: "sync" }),
    defaultValues: {
      styleSummary: makeEmptyStyleSummary(),
      promptPack: makeEmptyPromptPack(),
    },
  });

  React.useEffect(() => {
    initializedJobId.current = null;
    setStep(1);
    setMountProjectId(null);
    form.reset({
      styleSummary: makeEmptyStyleSummary(),
      promptPack: makeEmptyPromptPack(),
    });
  }, [jobId, form]);

  React.useEffect(() => {
    if (initializedJobId.current === jobId) return;

    if (existingProfile) {
      form.reset({
        styleSummary: existingProfile.style_summary,
        promptPack: existingProfile.prompt_pack,
      });
      initializedJobId.current = jobId;
      return;
    }

    if (job?.status === STYLE_ANALYSIS_JOB_STATUS.SUCCEEDED && summary && promptPack) {
      form.reset({
        styleSummary: summary,
        promptPack,
      });
      initializedJobId.current = jobId;
    }
  }, [existingProfile, form, job?.status, jobId, promptPack, summary]);

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
}: {
  job: StyleAnalysisJob | null;
  form: UseFormReturn<FormValues>;
  mountProjectId: string | null;
}) {
  const router = useRouter();

  return useMutation({
    mutationFn: async () => {
      const values = form.getValues();
      if (!job) throw new Error("缺少保存数据");

      const mountPayload = mountProjectId ? { mount_project_id: mountProjectId } : {};
      const payload = {
        ...mountPayload,
        style_summary: values.styleSummary,
        prompt_pack: values.promptPack,
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
      router.push("/style-lab");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "保存失败");
    },
  });
}

export function useStyleLabWizardLogic(jobId: string) {
  const detail = useStyleLabJobDetail(jobId);
  const wizardState = useStyleLabWizardState({
    jobId,
    job: detail.job,
    existingProfile: detail.existingProfile,
    summary: detail.summaryResource.data,
    promptPack: detail.promptPackResource.data,
  });
  const projectsState = useMountableProjects(wizardState.step >= 3);
  const saveProfileMutation = useSaveStyleProfileMutation({
    job: detail.job,
    form: wizardState.form,
    mountProjectId: wizardState.mountProjectId,
  });

  return {
    ...wizardState,
    job: detail.job,
    projects: projectsState.projects,
    existingProfile: detail.existingProfile,
    reportResource: detail.reportResource,
    summaryResource: detail.summaryResource,
    promptPackResource: detail.promptPackResource,
    saveProfileMutation,
    handleSave: () => saveProfileMutation.mutate(),
    isLoading: detail.isLoading || projectsState.isLoading,
    errorState: detail.errorState,
  };
}
