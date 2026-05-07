"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeft, Clipboard, FileText, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { MarkdownPreview } from "@/components/markdown-preview";
import { PageError, PageLoading } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { RequestError } from "@/lib/request-error";
import {
  formatWorkflowDate,
  WORKFLOW_INTENT_LABELS,
  WORKFLOW_STATUS_LABELS,
} from "@/lib/workflow-run-labels";

const PROMPT_TRACE_ARTIFACT = "prompt_trace_markdown";

export function WorkflowRunDetailView({ runId }: { runId: string }) {
  const [traceMode, setTraceMode] = useState<"preview" | "raw">("raw");
  const [logOffset, setLogOffset] = useState(0);
  const [logs, setLogs] = useState("");
  const logViewportRef = useRef<HTMLDivElement>(null);

  const runQuery = useQuery({
    queryKey: ["novel-workflow", runId],
    queryFn: () => api.getNovelWorkflow(runId),
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

      <Tabs defaultValue="trace" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trace">Prompt Trace</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="request">Request</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
        </TabsList>

        <TabsContent value="trace">
          <Card>
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
                  <ScrollArea className="h-[70vh] rounded-lg border bg-zinc-950 text-zinc-100">
                    <pre className="min-w-0 whitespace-pre-wrap break-words p-4 text-xs leading-relaxed">
                      {trace}
                    </pre>
                  </ScrollArea>
                ) : (
                  <ScrollArea className="h-[70vh] rounded-lg border bg-background">
                    <div className="p-4">
                      <MarkdownPreview content={trace} />
                    </div>
                  </ScrollArea>
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
