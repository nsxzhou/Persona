const plotLabJobsRoot = ["plot-lab", "jobs"] as const;

export const plotLabQueryKeys = {
  jobs: {
    root: plotLabJobsRoot,
    lists: () => [...plotLabJobsRoot, "list"] as const,
    list: (page: number) => [...plotLabQueryKeys.jobs.lists(), page] as const,
    detail: (jobId: string) => [...plotLabJobsRoot, "detail", jobId] as const,
    status: (jobId: string) => [...plotLabJobsRoot, "status", jobId] as const,
    logs: (jobId: string) => [...plotLabJobsRoot, "logs", jobId] as const,
    analysisReport: (jobId: string) => [...plotLabJobsRoot, "analysis-report", jobId] as const,
    plotSummary: (jobId: string) => [...plotLabJobsRoot, "plot-summary", jobId] as const,
    plotSkeleton: (jobId: string) => [...plotLabJobsRoot, "plot-skeleton", jobId] as const,
    promptPack: (jobId: string) => [...plotLabJobsRoot, "prompt-pack", jobId] as const,
  },
} as const;
