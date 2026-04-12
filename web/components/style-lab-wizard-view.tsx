"use client";

import { ArrowLeft, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageError, PageLoading } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { StyleLabWizardPromptPackStep } from "@/components/style-lab-wizard-prompt-pack-step";
import { StyleLabWizardReportStep } from "@/components/style-lab-wizard-report-step";
import { StyleLabWizardSummaryStep } from "@/components/style-lab-wizard-summary-step";
import { useStyleLabWizardLogic } from "@/hooks/use-style-lab-wizard-logic";
import { STYLE_ANALYSIS_JOB_STATUS } from "@/lib/types";

export function StyleLabWizardView({ jobId }: { jobId: string }) {
  const {
    step,
    setStep,
    mountProjectId,
    setMountProjectId,
    form,
    job,
    projects,
    existingProfile,
    reportResource,
    summaryResource,
    promptPackResource,
    saveProfileMutation,
    handleStep2Next,
    handleSave,
    isLoading,
    errorState,
  } = useStyleLabWizardLogic(jobId);

  if (isLoading) {
    return <PageLoading title="加载中..." />;
  }
  if (errorState) return <PageError title={errorState.title} message={errorState.message} />;
  if (!job) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/style-lab"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{job.style_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={job.status === STYLE_ANALYSIS_JOB_STATUS.FAILED ? "destructive" : "secondary"}>{job.status}</Badge>
            <span className="text-sm text-muted-foreground">模型: {job.model_name}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center border-b pb-6">
        <div className="flex items-center gap-2">
          <div className={cn("flex items-center justify-center w-8 h-8 rounded-full", step >= 1 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground")}>
            {step > 1 ? <CheckCircle2 className="w-5 h-5" /> : 1}
          </div>
          <span className={cn("text-sm font-medium", step >= 1 ? "text-foreground" : "text-muted-foreground")}>分析报告</span>
        </div>
        <div className={cn("w-16 h-1 mx-2 rounded-full", step >= 2 ? "bg-primary" : "bg-muted")} />
        <div className="flex items-center gap-2">
          <div className={cn("flex items-center justify-center w-8 h-8 rounded-full", step >= 2 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground")}>
            {step > 2 ? <CheckCircle2 className="w-5 h-5" /> : 2}
          </div>
          <span className={cn("text-sm font-medium", step >= 2 ? "text-foreground" : "text-muted-foreground")}>风格摘要</span>
        </div>
        <div className={cn("w-16 h-1 mx-2 rounded-full", step >= 3 ? "bg-primary" : "bg-muted")} />
        <div className="flex items-center gap-2">
          <div className={cn("flex items-center justify-center w-8 h-8 rounded-full", step >= 3 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground")}>
            3
          </div>
          <span className={cn("text-sm font-medium", step >= 3 ? "text-foreground" : "text-muted-foreground")}>母 Prompt</span>
        </div>
      </div>

      {step === 1 ? (
        <StyleLabWizardReportStep
          job={job}
          existingProfile={existingProfile}
          reportMarkdown={reportResource.data}
          isLoading={reportResource.isLoading}
          isError={reportResource.isError}
          errorMessage={reportResource.error?.message}
          onNext={() => setStep(2)}
        />
      ) : null}

      {step === 2 ? (
        <StyleLabWizardSummaryStep
          job={job}
          existingProfile={existingProfile}
          summaryMarkdown={summaryResource.data}
          isLoading={summaryResource.isLoading}
          isError={summaryResource.isError}
          errorMessage={summaryResource.error?.message}
          form={form}
          onBack={() => setStep(1)}
          onNext={handleStep2Next}
        />
      ) : null}

      {step === 3 ? (
        <StyleLabWizardPromptPackStep
          job={job}
          existingProfile={existingProfile}
          promptPackMarkdown={promptPackResource.data}
          isLoading={promptPackResource.isLoading}
          isError={promptPackResource.isError}
          errorMessage={promptPackResource.error?.message}
          projects={projects}
          mountProjectId={mountProjectId}
          setMountProjectId={setMountProjectId}
          form={form}
          onBack={() => setStep(2)}
          onSave={handleSave}
          saving={saveProfileMutation.isPending}
        />
      ) : null}
    </div>
  );
}
