import { useMutation, useQuery } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import * as React from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { api } from "@/lib/api";
import {
  formSchema,
  type FormValues,
  makeEmptyStyleSummary,
  makeEmptyPromptPack,
} from "@/lib/validations/style-lab";

const NONE_VALUE = "__none__";

export function useStyleLabWizardLogic(jobId: string) {
  const router = useRouter();
  const [step, setStep] = React.useState<1 | 2 | 3>(1);
  const [mountProjectId, setMountProjectId] = React.useState<string | null>(null);
  
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema, undefined, { mode: "sync" }),
    defaultValues: {
      styleSummary: makeEmptyStyleSummary(),
      promptPack: makeEmptyPromptPack(),
    },
  });

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

  const job = jobQuery.data;
  const projects = projectsQuery.data ?? [];
  
  const profileQuery = useQuery({
    queryKey: ["style-profiles", job?.style_profile_id ?? NONE_VALUE],
    queryFn: async () => (await api.getStyleProfile(job?.style_profile_id ?? "")) ?? null,
    enabled: Boolean(job?.style_profile_id),
  });
  const existingProfile = profileQuery.data ?? null;

  const reportQuery = useQuery({
    queryKey: ["style-analysis-jobs", job?.id, "analysis-report"],
    queryFn: () => api.getStyleAnalysisJobAnalysisReport(job!.id),
    enabled: job?.status === "succeeded" && !existingProfile,
  });

  const summaryQuery = useQuery({
    queryKey: ["style-analysis-jobs", job?.id, "style-summary"],
    queryFn: () => api.getStyleAnalysisJobStyleSummary(job!.id),
    enabled: job?.status === "succeeded" && !existingProfile,
  });

  const promptPackQuery = useQuery({
    queryKey: ["style-analysis-jobs", job?.id, "prompt-pack"],
    queryFn: () => api.getStyleAnalysisJobPromptPack(job!.id),
    enabled: job?.status === "succeeded" && !existingProfile,
  });

  const isInitialized = React.useRef(false);

  React.useEffect(() => {
    if (isInitialized.current) return;

    if (existingProfile) {
      form.reset({
        styleSummary: existingProfile.style_summary,
        promptPack: existingProfile.prompt_pack,
      });
      isInitialized.current = true;
      return;
    }

    if (
      job?.status === "succeeded" &&
      summaryQuery.isSuccess &&
      promptPackQuery.isSuccess
    ) {
      form.reset({
        styleSummary: summaryQuery.data,
        promptPack: promptPackQuery.data,
      });
      isInitialized.current = true;
    }
  }, [existingProfile, job?.status, summaryQuery.isSuccess, summaryQuery.data, promptPackQuery.isSuccess, promptPackQuery.data, form]);

  const handleStep2Next = async () => {
    setStep(3);
  };

  const saveProfileMutation = useMutation({
    mutationFn: async () => {
      const values = form.getValues();
      if (!job) throw new Error("缺少保存数据");
      if (job.style_profile_id) {
        const profile = await api.updateStyleProfile(job.style_profile_id, {
          style_summary: values.styleSummary,
          prompt_pack: values.promptPack,
        });
        if (mountProjectId) {
          await api.updateProject(mountProjectId, { style_profile_id: profile.id });
        }
        return profile;
      } else {
        const profile = await api.createStyleProfile({
          job_id: job.id,
          style_summary: values.styleSummary,
          prompt_pack: values.promptPack,
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

  const handleSave = () => {
    saveProfileMutation.mutate();
  };

  const isLoading = jobQuery.isLoading || projectsQuery.isLoading || profileQuery.isLoading;
  const isError = jobQuery.isError || profileQuery.isError || !job;
  
  let errorState = null;
  if (jobQuery.isError) errorState = { title: "加载任务失败", message: jobQuery.error.message };
  else if (profileQuery.isError) errorState = { title: "加载风格档案失败", message: profileQuery.error.message };
  else if (!isLoading && !job) errorState = { title: "任务不存在", message: "未找到对应的风格分析任务" };

  return {
    step,
    setStep,
    mountProjectId,
    setMountProjectId,
    form,
    job,
    projects,
    existingProfile,
    reportQuery,
    summaryQuery,
    promptPackQuery,
    saveProfileMutation,
    handleStep2Next,
    handleSave,
    isLoading,
    errorState,
  };
}
