import { useQuery } from "@tanstack/react-query";
import * as React from "react";

const LOG_WINDOW_SIZE = 64 * 1024;

export type AnalysisJobLogsPayload = {
  content: string;
  next_offset: number;
  truncated: boolean;
};

export function useAnalysisJobLogsQuery<TLogs extends AnalysisJobLogsPayload>({
  jobId,
  isProcessing,
  queryKey,
  queryFn,
  refetchOnWindowFocus,
  staleTime,
}: {
  jobId: string;
  isProcessing: boolean;
  queryKey: readonly unknown[];
  queryFn: (offset: number) => Promise<TLogs>;
  refetchOnWindowFocus?: boolean;
  staleTime?: number;
}) {
  const offsetRef = React.useRef(0);
  const [logs, setLogs] = React.useState("");

  React.useEffect(() => {
    offsetRef.current = 0;
    setLogs("");
  }, [jobId]);

  const query = useQuery<TLogs>({
    queryKey,
    queryFn: () => queryFn(offsetRef.current),
    refetchInterval: isProcessing ? 1000 : false,
    refetchOnWindowFocus,
    staleTime,
  });

  React.useEffect(() => {
    const payload = query.data;
    if (!payload) return;
    setLogs((prev) => {
      const next = payload.truncated ? payload.content : prev + payload.content;
      return next.slice(-LOG_WINDOW_SIZE);
    });
    offsetRef.current = payload.next_offset;
  }, [query.data]);

  return {
    ...query,
    logs,
  };
}
