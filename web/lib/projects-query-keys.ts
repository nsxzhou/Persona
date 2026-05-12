export const PROJECTS_PAGE_SIZE = 10;

export const projectsQueryKeys = {
  all: ["projects"] as const,
  list: (includeArchived: boolean, page: number) =>
    [...projectsQueryKeys.all, includeArchived, page] as const,
  workflowFilter: () => [...projectsQueryKeys.all, "workflow-filter"] as const,
  importProviders: () => ["provider-configs"] as const,
  importStyleProfiles: () => ["style-profiles", "import-txt"] as const,
  importPlotProfiles: () => ["plot-profiles", "import-txt"] as const,
} as const;
