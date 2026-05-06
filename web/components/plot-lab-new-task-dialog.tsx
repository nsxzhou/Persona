"use client";

import { LabNewTaskDialog } from "@/components/lab-new-task-dialog";
import { api } from "@/lib/api";
import { plotLabQueryKeys } from "@/lib/plot-lab-query-keys";
import type { PlotAnalysisJobCreatePayload, ProviderConfig } from "@/lib/types";

export function PlotLabNewTaskDialog({ providers }: { providers: ProviderConfig[] }) {
  return (
    <LabNewTaskDialog<PlotAnalysisJobCreatePayload & { file: File }>
      providers={providers}
      nameLabel="情节档案名称"
      namePlaceholder="例如：反派修罗场模板"
      nameRequiredMessage="请输入情节档案名称"
      description="上传样本，创建新的情节分析任务。"
      inputIdPrefix="plot"
      redirectBasePath="/plot-lab"
      listQueryKey={plotLabQueryKeys.jobs.lists()}
      createJob={api.createPlotAnalysisJob}
      buildPayload={(values) => ({
        plot_name: values.name.trim(),
        provider_id: values.provider_id,
        model: values.model.trim() || undefined,
        file: values.file as File,
      })}
    />
  );
}
