"use client";

import { ArrowLeft, CheckCircle2, Info } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageError, PageLoading } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { StyleLabWizardReportStep } from "@/components/style-lab-wizard-report-step";
import { StyleLabWizardSummaryStep } from "@/components/style-lab-wizard-summary-step";
import { StyleLabProfileView } from "@/components/style-lab-profile-view";
import { useStyleLabWizardLogic, isProcessingStatus } from "@/hooks/use-style-lab-wizard-logic";

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
    voiceProfileResource,
    saveProfileMutation,
    resumeJobMutation,
    pauseJobMutation,
    handleSave,
    handleResume,
    handlePause,
    isLoading,
    errorState,
    isEditing,
    setIsEditing,
  } = useStyleLabWizardLogic(jobId);

  if (isLoading) {
    return <PageLoading title="加载中..." />;
  }
  if (errorState) return <PageError title={errorState.title} message={errorState.message} />;
  if (!job) return null;

  const isCompletedAndSaved = job.status === "succeeded" && existingProfile;

  if (isCompletedAndSaved) {
    return (
      <StyleLabProfileView 
        job={job} 
        profile={existingProfile} 
        isEditing={isEditing}
        onEditStart={() => setIsEditing(true)} 
        onEditCancel={() => setIsEditing(false)}
        onSave={handleSave}
        saving={saveProfileMutation.isPending}
        form={form}
      />
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      {isProcessingStatus(job.status) && (
        <Alert className="bg-primary/5 border-primary/20">
          <Info className="h-4 w-4 text-primary" />
          <AlertTitle className="text-primary font-medium">任务已在后台安全运行</AlertTitle>
          <AlertDescription className="text-muted-foreground">
            您可以随时离开此页面。分析完成后，任务记录将保存在您的工作台中。
          </AlertDescription>
        </Alert>
      )}
      
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/style-lab"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{job.style_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={job.status === "failed" ? "destructive" : "secondary"}>{job.status}</Badge>
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
            2
          </div>
          <span className={cn("text-sm font-medium", step >= 2 ? "text-foreground" : "text-muted-foreground")}>Voice Profile</span>
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
          onResume={handleResume}
          resuming={resumeJobMutation.isPending}
          onPause={handlePause}
          pausing={pauseJobMutation.isPending}
          onNext={() => setStep(2)}
        />
      ) : null}

      {step === 2 ? (
        <StyleLabWizardSummaryStep
          job={job}
          existingProfile={existingProfile}
          voiceProfileMarkdown={voiceProfileResource.data}
          isLoading={voiceProfileResource.isLoading}
          isError={voiceProfileResource.isError}
          errorMessage={voiceProfileResource.error?.message}
          form={form}
          onBack={() => setStep(1)}
          onNext={handleSave}
        />
      ) : null}
    </div>
  );
}
