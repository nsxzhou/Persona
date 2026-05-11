"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, ExternalLink, GitCompareArrows } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export function ChapterRewriteBatchDetailView({ batchId }: { batchId: string }) {
  const batchQuery = useQuery({
    queryKey: ["chapter-rewrite-batch-detail", batchId],
    queryFn: () => api.getChapterRewriteBatch(batchId),
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "running" ? 1000 : false,
  });

  const batch = batchQuery.data;

  if (batchQuery.isLoading) {
    return <div className="p-8 text-sm text-muted-foreground">加载中...</div>;
  }
  if (!batch) {
    return <div className="p-8 text-sm text-muted-foreground">章节改写任务不存在。</div>;
  }
  const items = batch.items ?? [];

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-5 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
            <GitCompareArrows className="h-4 w-4" />
            章节改写任务
          </div>
          <h1 className="text-2xl font-semibold">批量改写状态</h1>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href={`/projects/${batch.project_id}/editor`}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              回到编辑器审核
            </Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">概览</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm md:grid-cols-5">
          <Metric label="状态" value={batch.status} />
          <Metric label="阶段" value={batch.stage ?? "-"} />
          <Metric label="总数" value={String(batch.total_count)} />
          <Metric label="已生成" value={String(batch.generated_count)} />
          <Metric label="失败" value={String(batch.failed_count)} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">条目</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className="grid gap-2 rounded-md border p-3 text-sm md:grid-cols-[minmax(0,1fr)_120px_120px_160px]"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{item.chapter_title ?? item.chapter?.title ?? item.chapter_id}</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">{item.error_message ?? item.stage ?? item.child_run_id ?? "等待处理"}</p>
              </div>
              <span>{item.status}</span>
              <span>{item.child_run_id ? "有日志" : "无日志"}</span>
              <div className="flex justify-end gap-2">
                {item.child_run_id ? (
                  <Button asChild variant="ghost" size="sm">
                    <a href={`/api/v1/chapter-rewrite-batches/${batch.id}/items/${item.id}/logs`}>
                      日志
                    </a>
                  </Button>
                ) : null}
                {item.status === "generated" || item.status === "applied" ? (
                  <Button asChild variant="ghost" size="sm">
                    <a href={`/api/v1/chapter-rewrite-batches/${batch.id}/items/${item.id}/artifact`}>
                      产物
                    </a>
                  </Button>
                ) : null}
                {item.child_run_id ? (
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/workflow-runs/${item.child_run_id}`}>
                      <ExternalLink className="mr-2 h-4 w-4" />
                      子任务
                    </Link>
                  </Button>
                ) : null}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-muted/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}
