"use client";

import * as React from "react";

import { type PlotAnalysisJob, type PlotProfile } from "@/lib/types";
import { LabWizardReportStep } from "@/components/lab-wizard-report-step";
import {
  formatPlotStageLabel,
  isProcessingStatus,
  usePlotLabJobLogsQuery,
} from "@/hooks/use-plot-lab-wizard-logic";

export const PlotLabWizardReportStep = React.memo(function PlotLabWizardReportStep({
  job,
  existingProfile,
  reportMarkdown,
  isLoading,
  isError,
  errorMessage,
  onResume,
  resuming,
  onPause,
  pausing,
  onNext,
}: {
  job: PlotAnalysisJob;
  existingProfile: PlotProfile | null;
  reportMarkdown: string | null;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  onResume: () => void;
  resuming: boolean;
  onPause: () => void;
  pausing: boolean;
  onNext: () => void;
}) {
  const isProcessing = isProcessingStatus(job.status);
  const { logs } = usePlotLabJobLogsQuery(job.id, isProcessing);

  return (
    <LabWizardReportStep
      status={job.status}
      stage={job.stage}
      pauseRequestedAt={job.pause_requested_at}
      reportMarkdown={reportMarkdown}
      isLoading={isLoading}
      isError={isError}
      hasExistingProfile={Boolean(existingProfile)}
      errorMessage={job.status === "failed" ? job.error_message?.trim() || undefined : errorMessage}
      logs={logs}
      reportDescription="这是 AI 生成的 Markdown 情节分析报告，仅供审阅。"
      formatStageLabel={formatPlotStageLabel}
      onResume={onResume}
      resuming={resuming}
      onPause={onPause}
      pausing={pausing}
      onNext={onNext}
    />
  );
});
