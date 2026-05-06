export const providerQueryKeys = {
  all: ["provider-configs"] as const,
  lists: () => providerQueryKeys.all,
};
