import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { useForm, type UseFormReturn } from "react-hook-form";

import { api } from "@/lib/api";
import { profileQueryKeys } from "@/lib/profile-query-keys";
import { styleLabQueryKeys } from "@/lib/style-lab-query-keys";
import { formSchema, makeEmptyFormValues, type FormValues } from "@/lib/validations/style-lab";
import {
  type StyleAnalysisJobLogs,
  type StyleAnalysisJob,
  type StyleProfile,
  type StyleAnalysisJobStatusSnapshot,
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

type WizardStep = 1 | 2;

export function isProcessingStatus(status: StyleAnalysisJob["status"] | undefined) {
  return isAnalysisJobProcessingStatus(status);
}

export function useStyleLabJobLogsQuery(jobId: string, isProcessing: boolean) {
  return useAnalysisJobLogsQuery<StyleAnalysisJobLogs>({
    jobId,
    isProcessing,
    queryKey: styleLabQueryKeys.jobs.logs(jobId),
    queryFn: (offset) => api.getStyleAnalysisJobLogs(jobId, offset),
  });
}

function useStyleLabResourcesQueries(jobId: string, job: StyleAnalysisJob | null) {
  const existingProfileQuery = useQuery({
    queryKey: profileQueryKeys.style.detail(job?.style_profile_id),
    queryFn: () => api.getStyleProfile(String(job?.style_profile_id)),
    enabled: Boolean(job?.style_profile_id),
  });

  const isCompletedAndNoProfile = Boolean(job && job.status === "succeeded" && !job.style_profile_id);
  const needsReport = isCompletedAndNoProfile;
  const needsVoiceProfile = isCompletedAndNoProfile;

  const reportQuery = useQuery({
    queryKey: styleLabQueryKeys.jobs.analysisReport(jobId),
    queryFn: () => api.getStyleAnalysisJobAnalysisReport(jobId),
    enabled: needsReport,
  });
  
  const voiceProfileQuery = useQuery({
    queryKey: styleLabQueryKeys.jobs.voiceProfile(jobId),
    queryFn: () => api.getStyleAnalysisJobVoiceProfile(jobId),
    enabled: needsVoiceProfile,
  });

  return { existingProfileQuery, reportQuery, voiceProfileQuery };
}

function mergeJobResources(
  job: StyleAnalysisJob | null,
  queries: ReturnType<typeof useStyleLabResourcesQueries>
) {
  const { existingProfileQuery, reportQuery, voiceProfileQuery } = queries;
  const existingProfile = existingProfileQuery.data ?? null;

  const report = existingProfile?.analysis_report_markdown ?? reportQuery.data ?? null;
  const voiceProfile = existingProfile?.voice_profile_markdown ?? voiceProfileQuery.data ?? null;
  const useExistingProfileQuery = Boolean(job?.style_profile_id);

  return {
    existingProfile,
    reportResource: makeAnalysisArtifactResource<string>({
      value: report,
      artifactQuery: reportQuery,
      existingProfileQuery,
      useExistingProfileQuery,
    }),
    voiceProfileResource: makeAnalysisArtifactResource<string>({
      value: voiceProfile,
      artifactQuery: voiceProfileQuery,
      existingProfileQuery,
      useExistingProfileQuery,
    }),
  };
}

function useStyleLabJobDetail(jobId: string) {
  const { statusQuery, jobQuery } = useAnalysisJobQueries<
    StyleAnalysisJob,
    StyleAnalysisJobStatusSnapshot
  >({
    statusQueryKey: styleLabQueryKeys.jobs.status(jobId),
    statusQueryFn: () => api.getStyleAnalysisJobStatus(jobId),
    detailQueryKey: styleLabQueryKeys.jobs.detail(jobId),
    detailQueryFn: () => api.getStyleAnalysisJob(jobId),
    isProcessingStatus,
  });

  useRefreshAnalysisJobDetailWhenSucceeded({
    status: statusQuery.data?.status,
    detailStatus: jobQuery.data?.status,
    isDetailFetching: jobQuery.isFetching,
    refetchDetail: jobQuery.refetch,
  });

  const job = mergeAnalysisStatusIntoJob(jobQuery.data ?? null, statusQuery.data ?? null);
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

function useStyleLabWizardState({
  jobId,
  job,
  existingProfile,
  voiceProfileMarkdown,
}: {
  jobId: string;
  job: StyleAnalysisJob | null;
  existingProfile: StyleProfile | null;
  voiceProfileMarkdown: string | null;
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
        styleName: existingProfile.style_name,
        voiceProfileMarkdown: existingProfile.voice_profile_markdown,
      });
      initializedJobId.current = jobId;
      return;
    }

    if (job?.status === "succeeded" && voiceProfileMarkdown) {
      form.reset({
        styleName: job.style_name,
        voiceProfileMarkdown,
      });
      initializedJobId.current = jobId;
    }
  }, [existingProfile, form, job, jobId, voiceProfileMarkdown]);

  return {
    step,
    setStep,
    form,
    handleStep2Next: () => setStep(2),
  };
}

function useSaveStyleProfileMutation({
  job,
  form,
  onSuccessCallback,
}: {
  job: StyleAnalysisJob | null;
  form: UseFormReturn<FormValues>;
  onSuccessCallback?: () => void;
}) {
  return useAnalysisProfileSaveMutation({
    mutationFn: async () => {
      const values = form.getValues();
      if (!job) throw new Error("缺少保存数据");

      const payload = {
        style_name: values.styleName,
        voice_profile_markdown: values.voiceProfileMarkdown,
      };

      if (job.style_profile_id) {
        return api.updateStyleProfile(job.style_profile_id, payload);
      }

      return api.createStyleProfile({
        ...payload,
        job_id: job.id,
      });
    },
    successMessage: "风格档案已保存",
    onSuccessCallback,
    editProfileQueryKey: profileQueryKeys.style.detail(job?.style_profile_id),
    editJobQueryKey: job?.id ? styleLabQueryKeys.jobs.detail(job.id) : undefined,
    redirectPath: "/style-lab",
  });
}

function useResumeStyleAnalysisJobMutation(jobId: string) {
  return useAnalysisJobCommandMutation({
    jobId,
    mutationFn: api.resumeStyleAnalysisJob,
    successMessage: "任务已恢复",
    detailQueryKey: styleLabQueryKeys.jobs.detail(jobId),
    listsQueryKey: styleLabQueryKeys.jobs.lists(),
  });
}

function usePauseStyleAnalysisJobMutation(jobId: string) {
  return useAnalysisJobCommandMutation({
    jobId,
    mutationFn: api.pauseStyleAnalysisJob,
    successMessage: "已发送暂停请求",
    detailQueryKey: styleLabQueryKeys.jobs.detail(jobId),
    listsQueryKey: styleLabQueryKeys.jobs.lists(),
  });
}

export function useStyleLabWizardLogic(jobId: string) {
  const [isEditing, setIsEditing] = React.useState(false);
  const detail = useStyleLabJobDetail(jobId);
  const wizardState = useStyleLabWizardState({
    jobId,
    job: detail.job,
    existingProfile: detail.existingProfile,
    voiceProfileMarkdown: detail.voiceProfileResource.data,
  });
  const saveProfileMutation = useSaveStyleProfileMutation({
    job: detail.job,
    form: wizardState.form,
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
    voiceProfileResource: detail.voiceProfileResource,
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
