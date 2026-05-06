const styleProfilesRoot = ["style-profiles"] as const;
const plotProfilesRoot = ["plot-profiles"] as const;

export const profileQueryKeys = {
  style: {
    all: styleProfilesRoot,
    detail: (profileId: string | null | undefined) => [...styleProfilesRoot, profileId] as const,
  },
  plot: {
    all: plotProfilesRoot,
    detail: (profileId: string | null | undefined) => [...plotProfilesRoot, profileId] as const,
  },
};
