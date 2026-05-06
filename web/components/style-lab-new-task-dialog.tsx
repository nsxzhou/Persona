"use client";

import { LabNewTaskDialog } from "@/components/lab-new-task-dialog";
import { api } from "@/lib/api";
import { styleLabQueryKeys } from "@/lib/style-lab-query-keys";
import type { ProviderConfig, StyleAnalysisJobCreatePayload } from "@/lib/types";

export function StyleLabNewTaskDialog({ providers }: { providers: ProviderConfig[] }) {
  return (
    <LabNewTaskDialog<StyleAnalysisJobCreatePayload & { file: File }>
      providers={providers}
      nameLabel="风格档案名称"
      namePlaceholder="例如：金庸武侠风"
      nameRequiredMessage="请输入风格档案名称"
      description="上传样本，创建新的风格分析任务。"
      inputIdPrefix="style"
      redirectBasePath="/style-lab"
      listQueryKey={styleLabQueryKeys.jobs.lists()}
      createJob={api.createStyleAnalysisJob}
      buildPayload={(values) => ({
        style_name: values.name.trim(),
        provider_id: values.provider_id,
        model: values.model.trim() || undefined,
        file: values.file as File,
      })}
    />
  );
}
