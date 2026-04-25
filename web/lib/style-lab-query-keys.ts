const styleLabJobsRoot = ["style-lab", "jobs"] as const;
const styleLabJobListsRoot = [...styleLabJobsRoot, "list"] as const;
const styleLabJobDetailsRoot = [...styleLabJobsRoot, "detail"] as const;

export const styleLabQueryKeys = {
  jobs: {
    all: styleLabJobsRoot,
    lists: () => styleLabJobListsRoot,
    list: (page: number) => [...styleLabJobListsRoot, page] as const,
    details: () => styleLabJobDetailsRoot,
    detail: (jobId: string) => [...styleLabJobDetailsRoot, jobId] as const,
    status: (jobId: string) => [...styleLabJobDetailsRoot, jobId, "status"] as const,
    logs: (jobId: string) => [...styleLabJobDetailsRoot, jobId, "logs"] as const,
    analysisReport: (jobId: string) =>
      [...styleLabJobDetailsRoot, jobId, "analysis-report"] as const,
    voiceProfile: (jobId: string) =>
      [...styleLabJobDetailsRoot, jobId, "voice-profile"] as const,
  },
};
