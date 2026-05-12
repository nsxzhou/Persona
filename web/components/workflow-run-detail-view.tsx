"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft, Clipboard, FileText, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import {
  parsePromptTraceMarkdown,
  type PromptTraceCall,
  type PromptTraceParseResult,
  type PromptTraceSegment,
  type PromptTraceTable,
} from "@/lib/prompt-trace-parser";
import { RequestError } from "@/lib/request-error";
import {
  formatWorkflowDate,
  WORKFLOW_INTENT_LABELS,
  WORKFLOW_STATUS_LABELS,
} from "@/lib/workflow-run-labels";

const PROMPT_TRACE_ARTIFACT = "prompt_trace_markdown";

export function WorkflowRunDetailView({ runId }: { runId: string }) {
  const [traceMode, setTraceMode] = useState<"preview" | "raw">("preview");
  const [logOffset, setLogOffset] = useState(0);
  const [logs, setLogs] = useState("");
  const logViewportRef = useRef<HTMLDivElement>(null);

  const runQuery = useQuery({
    queryKey: ["novel-workflow", runId],
    queryFn: () => api.getNovelWorkflow(runId),
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "running" ? 1000 : false,
  });

  const traceQuery = useQuery({
    queryKey: ["novel-workflow-artifact", runId, PROMPT_TRACE_ARTIFACT],
    queryFn: async () => {
      try {
        return await api.getNovelWorkflowArtifact(runId, PROMPT_TRACE_ARTIFACT);
      } catch (error) {
        if (error instanceof RequestError && error.status === 404) {
          return "";
        }
        throw error;
      }
    },
    enabled: runQuery.isSuccess,
  });

  const logsQuery = useQuery({
    queryKey: ["novel-workflow-logs", runId, logOffset],
    queryFn: () => api.getNovelWorkflowLogs(runId, logOffset),
    enabled: runQuery.isSuccess,
  });

  useEffect(() => {
    if (!logsQuery.data) return;
    setLogs((current) =>
      logsQuery.data?.truncated ? logsQuery.data.content : current + logsQuery.data.content,
    );
    setLogOffset(logsQuery.data.next_offset);
  }, [logsQuery.data]);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      const viewport = logViewportRef.current?.querySelector(
        "[data-radix-scroll-area-viewport]",
      ) as HTMLDivElement | null;
      if (viewport) viewport.scrollTop = viewport.scrollHeight;
    }, 0);
    return () => clearTimeout(timeoutId);
  }, [logs]);

  const artifactNames = useMemo(
    () => runQuery.data?.latest_artifacts?.filter((name) => name !== PROMPT_TRACE_ARTIFACT) ?? [],
    [runQuery.data?.latest_artifacts],
  );

  if (runQuery.isLoading) {
    return <PageLoading title="正在加载 Workflow Run..." />;
  }

  if (runQuery.isError || !runQuery.data) {
    return (
      <PageError
        title="运行记录加载失败"
        message={runQuery.error instanceof Error ? runQuery.error.message : "请重试"}
      />
    );
  }

  const run = runQuery.data;
  const trace = traceQuery.data ?? "";
  const parsedTrace = trace.trim() ? parsePromptTraceMarkdown(trace) : null;

  const copyTrace = async () => {
    if (!trace.trim()) {
      toast.message("当前 run 暂无 Prompt Trace");
      return;
    }
    await navigator.clipboard.writeText(trace);
    toast.success("Prompt Trace 已复制");
  };

  return (
    <section className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/workflow-runs" aria-label="返回运行历史">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-bold tracking-tight">
            {WORKFLOW_INTENT_LABELS[run.intent_type]} / Prompt Trace
          </h1>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{run.id}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <SummaryCard label="状态" value={WORKFLOW_STATUS_LABELS[run.status]}>
          <Badge variant={run.status === "failed" ? "destructive" : "secondary"}>
            {WORKFLOW_STATUS_LABELS[run.status]}
          </Badge>
        </SummaryCard>
        <SummaryCard label="项目" value={run.project_name || run.project_id || "无项目"} />
        <SummaryCard label="模型" value={run.model_name || "-"} description={run.provider_label || run.provider_id || ""} />
        <SummaryCard label="时间" value={formatWorkflowDate(run.created_at)} description={`完成：${formatWorkflowDate(run.completed_at)}`} />
      </div>

      {run.status === "failed" && run.error_message ? (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3">
          <p className="text-sm font-medium text-destructive">错误信息</p>
          <p className="mt-1 text-sm text-destructive/80">{run.error_message}</p>
        </div>
      ) : null}

      <Tabs defaultValue="trace" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trace">Prompt Trace</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="request">Request</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
        </TabsList>

        <TabsContent value="trace">
          <Card className="mx-auto max-w-6xl overflow-hidden">
            <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle className="text-lg">Prompt Trace</CardTitle>
                <CardDescription>
                  完整输入 prompt + 输出摘要。记录的是注入后的实际 LLM messages。
                </CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={traceMode === "raw" ? "secondary" : "outline"}
                  onClick={() => setTraceMode("raw")}
                >
                  Raw Markdown
                </Button>
                <Button
                  variant={traceMode === "preview" ? "secondary" : "outline"}
                  onClick={() => setTraceMode("preview")}
                >
                  渲染视图
                </Button>
                <Button variant="outline" onClick={copyTrace} className="gap-2">
                  <Clipboard className="h-4 w-4" />
                  复制全文
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {traceQuery.isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  正在读取 Prompt Trace...
                </div>
              ) : trace.trim() ? (
                traceMode === "raw" ? (
                  <RawPromptTrace content={trace} />
                ) : (
                  <PromptTraceRenderedView parsedTrace={parsedTrace} rawTrace={trace} />
                )
              ) : (
                <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                  当前 run 暂无 Prompt Trace。旧 run、未触发 LLM 的 run 或 trace 写入失败时会出现此状态。
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Execution Logs</CardTitle>
              <CardDescription>后台工作流日志。</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea ref={logViewportRef} className="h-[520px] rounded-lg border bg-zinc-950 text-zinc-100">
                <pre className="whitespace-pre-wrap break-words p-4 text-xs leading-relaxed">
                  {logs || "暂无日志。"}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="request">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Request Payload</CardTitle>
              <CardDescription>创建 workflow run 时保存的请求参数。</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto rounded-lg border bg-zinc-50 p-4 text-xs leading-relaxed text-zinc-900">
                {JSON.stringify(run.request_payload, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="artifacts">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Artifacts</CardTitle>
              <CardDescription>本次 run 的业务产物；Prompt Trace 不计入 latest artifacts。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {artifactNames.length > 0 ? (
                artifactNames.map((name) => (
                  <div key={name} className="flex items-center gap-2 rounded-md border p-3 text-sm">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="font-mono">{name}</span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">暂无业务产物。</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </section>
  );
}

function RawPromptTrace({ content }: { content: string }) {
  return (
    <ScrollArea className="h-[70vh] rounded-lg border bg-zinc-950 text-zinc-100">
      <pre className="min-w-0 whitespace-pre-wrap break-words p-4 text-xs leading-relaxed">
        {content}
      </pre>
    </ScrollArea>
  );
}

function PromptTraceRenderedView({
  parsedTrace,
  rawTrace,
}: {
  parsedTrace: PromptTraceParseResult | null;
  rawTrace: string;
}) {
  if (!parsedTrace) {
    return <RawPromptTrace content={rawTrace} />;
  }

  return (
    <ScrollArea className="h-[70vh] rounded-lg border bg-muted/20">
      <div className="min-w-0 space-y-4 p-4">
        <TraceSummary parsedTrace={parsedTrace} />
        <div className="space-y-3">
          {parsedTrace.calls.map((call) => (
            <PromptTraceCallCard key={call.index} call={call} />
          ))}
        </div>
      </div>
    </ScrollArea>
  );
}

function TraceSummary({ parsedTrace }: { parsedTrace: PromptTraceParseResult }) {
  const compactMetrics = [
    ["Calls", parsedTrace.summary.Calls],
    ["Failed calls", parsedTrace.summary["Failed calls"]],
    ["Total input chars", parsedTrace.summary["Total input chars"]],
    ["Contains truncation marker", parsedTrace.summary["Contains truncation marker"]],
  ].filter((entry): entry is [string, string] => Boolean(entry[1]));

  return (
    <div className="rounded-lg border bg-background px-4 py-3">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <h2 className="text-base font-semibold">Trace Summary</h2>
          <p className="text-xs text-muted-foreground">紧凑总览；重点内容在各 Call 内按 System/User/Output 查看。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {compactMetrics.map(([label, value]) => (
            <SummaryMetric key={label} label={label} value={value} />
          ))}
        </div>
      </div>

      <details className="group mt-3 rounded-md border bg-muted/20 px-3 py-2">
        <summary className="cursor-pointer list-none text-xs text-muted-foreground">
          <span className="group-open:hidden">展开完整 summary 数据</span>
          <span className="hidden group-open:inline">收起完整 summary 数据</span>
        </summary>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {Object.entries(parsedTrace.summary).map(([label, value]) => (
            <MetadataItem key={label} label={label} value={value} />
          ))}
        </div>
      </details>
    </div>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[120px] rounded-md border bg-muted/30 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate font-mono text-sm" title={value}>
        {value}
      </p>
    </div>
  );
}

function PromptTraceCallCard({ call }: { call: PromptTraceCall }) {
  const segments = orderPromptTraceSegments(call.segments);
  const outputSegment = segments.find((segment) => segment.kind === "output");
  const error = call.metadata.Error;
  const outputFallback = outputSegment?.fallbackText;
  const hasTruncation = call.metadata["Contains truncation marker"];

  return (
    <details className="group rounded-lg border bg-background p-4" open>
      <summary className="cursor-pointer list-none">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold">Call {call.index}</h3>
              <Badge variant="outline">{call.stage}</Badge>
              <Badge variant="secondary">{call.mode}</Badge>
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <span className="min-w-0 truncate">model {call.metadata.Model || "-"}</span>
              <span>input {call.metadata["Total input chars"] || "-"} chars</span>
              <span>output {call.metadata["Output chars"] || "-"} chars</span>
              <span>truncated {hasTruncation || "-"}</span>
            </div>
            {error && error !== "-" ? <p className="line-clamp-2 text-xs text-destructive">error {error}</p> : null}
            {!error && outputFallback ? (
              <p className="line-clamp-2 text-xs text-muted-foreground">{outputFallback}</p>
            ) : null}
          </div>
          <span className="shrink-0 text-xs text-muted-foreground group-open:hidden">展开 Call</span>
          <span className="hidden shrink-0 text-xs text-muted-foreground group-open:inline">收起 Call</span>
        </div>
      </summary>

      <div className="mt-4 space-y-4">
        <div className="space-y-3">
          {segments.map((segment) => (
            <PromptTraceSegmentPanel key={segment.id} segment={segment} callIndex={call.index} />
          ))}
        </div>
        <details className="group rounded-md border bg-muted/20 px-3 py-2">
          <summary className="cursor-pointer list-none text-xs text-muted-foreground">
            <span className="group-open:hidden">展开精确数据</span>
            <span className="hidden group-open:inline">收起精确数据</span>
          </summary>
          <MetadataGrid metadata={call.metadata} className="mt-3" />
        </details>
      </div>
    </details>
  );
}

function MetadataGrid({ metadata, className = "" }: { metadata: PromptTraceTable; className?: string }) {
  return (
    <div className={`grid gap-2 md:grid-cols-2 xl:grid-cols-3 ${className}`}>
      {Object.entries(metadata).map(([label, value]) => (
        <MetadataItem key={label} label={label} value={value} />
      ))}
    </div>
  );
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md bg-muted/40 px-3 py-2">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="truncate font-mono text-xs" title={value}>
        {value}
      </p>
    </div>
  );
}

function PromptTraceSegmentPanel({
  segment,
  callIndex,
}: {
  segment: PromptTraceSegment;
  callIndex: number;
}) {
  const copySegment = async () => {
    await navigator.clipboard.writeText(segment.content);
    toast.success(`${segment.title} 已复制`);
  };

  return (
    <details className="group rounded-md border bg-muted/20">
      <summary className="cursor-pointer list-none px-3 py-2">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="font-medium">{segment.title}</p>
            <p className="text-xs text-muted-foreground">
              Call {callIndex} · {segment.content.length} chars
              {segment.metadata.Chars ? ` · recorded ${segment.metadata.Chars} chars` : ""}
              {segment.metadata["Contains truncation marker"]
                ? ` · truncated ${segment.metadata["Contains truncation marker"]}`
                : ""}
            </p>
          </div>
          <span className="shrink-0 text-xs text-muted-foreground group-open:hidden">展开正文</span>
          <span className="hidden shrink-0 text-xs text-muted-foreground group-open:inline">收起正文</span>
        </div>
      </summary>
      <div className="space-y-3 border-t p-3">
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={copySegment}
            className="gap-2"
            aria-label={`复制 ${segment.title}`}
          >
            <Clipboard className="h-3.5 w-3.5" />
            复制本段
          </Button>
        </div>
        <pre className="max-h-[420px] min-w-0 overflow-auto whitespace-pre-wrap break-words rounded-md bg-zinc-950 p-3 text-xs leading-relaxed text-zinc-100">
          {segment.content}
        </pre>
      </div>
    </details>
  );
}

function orderPromptTraceSegments(segments: PromptTraceSegment[]) {
  const preferredTitles = ["System message", "User message", "Output excerpt"];
  return [
    ...preferredTitles
      .map((title) => segments.find((segment) => segment.title === title))
      .filter((segment): segment is PromptTraceSegment => Boolean(segment)),
    ...segments.filter((segment) => !preferredTitles.includes(segment.title)),
  ];
}

function SummaryCard({
  label,
  value,
  description,
  children,
}: {
  label: string;
  value: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="space-y-2">
        <CardDescription>{label}</CardDescription>
        {children ?? <CardTitle className="truncate text-base">{value}</CardTitle>}
        {description ? <p className="truncate text-xs text-muted-foreground">{description}</p> : null}
      </CardHeader>
    </Card>
  );
}
