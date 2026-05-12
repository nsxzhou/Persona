import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import {
  makeDetailResource,
  type DetailQueryLike,
  type DetailResource,
} from "@/lib/wizard-utils";

const STATUS_POLL_INTERVAL_MS = 2000;

type AnalysisJobStatus = string | null | undefined;

type AnalysisJobWithStatus = {
  status: AnalysisJobStatus;
};

type AnalysisJobWithStatusFields = AnalysisJobWithStatus & {
  stage: unknown;
  error_message: unknown;
  updated_at: unknown;
};

type AnalysisJobStatusSnapshot = AnalysisJobWithStatusFields;

export function isAnalysisJobProcessingStatus(status: AnalysisJobStatus): boolean {
  return status === "pending" || status === "running";
}

export function mergeAnalysisStatusIntoJob<
  TJob extends AnalysisJobWithStatusFields,
>(
  job: TJob | null,
  statusSnapshot: AnalysisJobStatusSnapshot | null,
): TJob | null {
  if (!job || !statusSnapshot) return job;
  return {
    ...job,
    status: statusSnapshot.status,
    stage: statusSnapshot.stage,
    error_message: statusSnapshot.error_message,
    updated_at: statusSnapshot.updated_at,
  };
}

export function useAnalysisJobQueries<
  TJob extends AnalysisJobWithStatus,
  TStatusSnapshot extends AnalysisJobWithStatus,
>({
  statusQueryKey,
  statusQueryFn,
  detailQueryKey,
  detailQueryFn,
  isProcessingStatus = isAnalysisJobProcessingStatus,
}: {
  statusQueryKey: QueryKey;
  statusQueryFn: () => Promise<TStatusSnapshot>;
  detailQueryKey: QueryKey;
  detailQueryFn: () => Promise<TJob>;
  isProcessingStatus?: (status: TStatusSnapshot["status"] | undefined) => boolean;
}) {
  const statusQuery = useQuery({
    queryKey: statusQueryKey,
    queryFn: statusQueryFn,
    refetchInterval: (query) =>
      isProcessingStatus(query.state.data?.status) ? STATUS_POLL_INTERVAL_MS : false,
  });

  const jobQuery = useQuery({
    queryKey: detailQueryKey,
    queryFn: detailQueryFn,
  });

  return { statusQuery, jobQuery };
}

export function useRefreshAnalysisJobDetailWhenSucceeded<TStatus extends AnalysisJobStatus>({
  status,
  detailStatus,
  isDetailFetching,
  refetchDetail,
  oncePerCompletion = false,
}: {
  status: TStatus;
  detailStatus: TStatus;
  isDetailFetching: boolean;
  refetchDetail: () => unknown;
  oncePerCompletion?: boolean;
}) {
  const hasRequestedFinalDetailRef = React.useRef(false);

  React.useEffect(() => {
    if (status !== "succeeded") {
      hasRequestedFinalDetailRef.current = false;
      return;
    }

    if (
      detailStatus !== "succeeded" &&
      !isDetailFetching &&
      (!oncePerCompletion || !hasRequestedFinalDetailRef.current)
    ) {
      hasRequestedFinalDetailRef.current = true;
      void refetchDetail();
    }
  }, [detailStatus, isDetailFetching, oncePerCompletion, refetchDetail, status]);
}

export function makeAnalysisArtifactResource<TData>({
  value,
  artifactQuery,
  existingProfileQuery,
  useExistingProfileQuery,
}: {
  value: TData | null | undefined;
  artifactQuery: DetailQueryLike;
  existingProfileQuery: DetailQueryLike;
  useExistingProfileQuery: boolean;
}): DetailResource<TData> {
  const query = useExistingProfileQuery ? existingProfileQuery : artifactQuery;
  return makeDetailResource<TData>(value, {
    isLoading: value == null ? query.isLoading : false,
    isError: value == null ? query.isError : false,
    error: value == null ? query.error : null,
  });
}

export function useAnalysisJobCommandMutation<TData>({
  jobId,
  mutationFn,
  successMessage,
  detailQueryKey,
  listsQueryKey,
}: {
  jobId: string;
  mutationFn: (jobId: string) => Promise<TData>;
  successMessage: string;
  detailQueryKey: QueryKey;
  listsQueryKey: QueryKey;
}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => mutationFn(jobId),
    onSuccess: () => {
      toast.success(successMessage);
      void queryClient.invalidateQueries({ queryKey: detailQueryKey });
      void queryClient.invalidateQueries({ queryKey: listsQueryKey });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "未知错误");
    },
  });
}

export function useAnalysisProfileSaveMutation<TData>({
  mutationFn,
  successMessage,
  onSuccessCallback,
  editProfileQueryKey,
  editJobQueryKey,
  saveListsQueryKey,
  redirectPath,
}: {
  mutationFn: () => Promise<TData>;
  successMessage: string;
  onSuccessCallback?: () => void;
  editProfileQueryKey?: QueryKey;
  editJobQueryKey?: QueryKey;
  saveListsQueryKey?: QueryKey;
  redirectPath: string;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: () => {
      toast.success(successMessage);
      if (onSuccessCallback) {
        onSuccessCallback();
        if (editProfileQueryKey) {
          void queryClient.invalidateQueries({ queryKey: editProfileQueryKey });
        }
        if (editJobQueryKey) {
          void queryClient.invalidateQueries({ queryKey: editJobQueryKey });
        }
      } else {
        if (saveListsQueryKey) {
          void queryClient.invalidateQueries({ queryKey: saveListsQueryKey });
        }
        router.push(redirectPath);
      }
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "未知错误");
    },
  });
}
