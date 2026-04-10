"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { PageError, PageLoading } from "@/components/page-state";
import { StyleLabNewTaskDialog } from "@/components/style-lab-new-task-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function StyleLabPage() {
  const providersQuery = useQuery({
    queryKey: ["provider-configs"],
    queryFn: api.getProviderConfigs,
  });

  const jobsQuery = useQuery({
    queryKey: ["style-analysis-jobs"],
    queryFn: () => api.getStyleAnalysisJobs(),
  });

  if (providersQuery.isLoading || jobsQuery.isLoading) {
    return <PageLoading title="正在载入 Style Lab..." />;
  }

  if (providersQuery.isError || jobsQuery.isError) {
    return (
      <PageError
        title="加载失败"
        message={
          (providersQuery.error instanceof Error && providersQuery.error.message) ||
          (jobsQuery.error instanceof Error && jobsQuery.error.message) ||
          "未知错误"
        }
      />
    );
  }

  const providers = providersQuery.data ?? [];
  const jobs = jobsQuery.data ?? [];

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Style Lab Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            管理所有的风格分析任务。点击卡片进入完整分析流程。
          </p>
        </div>
        <StyleLabNewTaskDialog providers={providers} />
      </div>

      {jobs.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>还没有分析任务</CardTitle>
            <CardDescription>点击右上角新建任务上传样本。</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {jobs.map((job) => (
            <Card
              key={job.id}
              className="flex flex-col transition-all hover:ring-2 hover:ring-primary hover:border-transparent cursor-pointer overflow-hidden"
            >
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between gap-4">
                  <CardTitle className="text-lg leading-tight hover:underline line-clamp-1">
                    <Link href={`/style-lab/${job.id}`}>
                      {job.style_name}
                    </Link>
                  </CardTitle>
                  <Badge
                    variant={
                      job.status === "failed"
                        ? "destructive"
                        : job.status === "succeeded"
                          ? "default"
                          : "secondary"
                    }
                    className="shrink-0"
                  >
                    {job.status}
                  </Badge>
                </div>
                <CardDescription className="line-clamp-1 mt-2">
                  样本: {job.sample_file.original_filename}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1 pb-4">
                <div className="flex flex-col gap-2 text-xs text-muted-foreground bg-muted/50 rounded-md p-3">
                  <div className="flex justify-between">
                    <span>模型</span>
                    <strong
                      className="font-medium text-foreground truncate max-w-[120px] text-right"
                      title={job.model_name}
                    >
                      {job.model_name}
                    </strong>
                  </div>
                  {job.stage && (
                    <div className="flex justify-between">
                      <span>当前阶段</span>
                      <strong className="font-medium text-foreground text-right">{job.stage}</strong>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter className="pt-4 border-t bg-muted/20">
                <Button variant="secondary" size="sm" className="w-full" asChild>
                  <Link href={`/style-lab/${job.id}`}>进入工作台</Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
