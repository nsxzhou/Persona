export type DetailResource<T> = {
  data: T | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
};

export type DetailQueryLike = {
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
};

export function makeDetailResource<T>(
  data: T | null | undefined,
  query: DetailQueryLike,
): DetailResource<T> {
  return {
    data: data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
  };
}