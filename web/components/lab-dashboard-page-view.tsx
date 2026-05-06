"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { type ComponentType, useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";

import { PageError, PageLoading } from "@/components/page-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { PlotLabNewTaskDialog } from "@/components/plot-lab-new-task-dialog";
import { StyleLabNewTaskDialog } from "@/components/style-lab-new-task-dialog";
import { formatPlotStageLabel } from "@/hooks/use-plot-lab-wizard-logic";
import { api } from "@/lib/api";
import { plotLabQueryKeys } from "@/lib/plot-lab-query-keys";
import { providerQueryKeys } from "@/lib/provider-query-keys";
import { styleLabQueryKeys } from "@/lib/style-lab-query-keys";
import type { PlotAnalysisJobListItem, ProviderConfig, StyleAnalysisJobListItem } from "@/lib/types";

const PAGE_SIZE = 12;

type LabJobBase = {
  id: string;
  status: string;
  stage?: string | null;
  model_name: string;
  sample_file: {
    original_filename: string;
  };
};

type LabDashboardConfig<TJob extends LabJobBase> = {
  title: string;
  description: string;
  loadingTitle: string;
  emptyTitle: string;
  emptyDescription: string;
  detailPathPrefix: string;
  newTaskDialog: ComponentType<{ providers: ProviderConfig[] }>;
  jobsListQueryKey: readonly unknown[];
  getJobsQueryKey: (page: number) => readonly unknown[];
  getJobDetailQueryKey: (jobId: string) => readonly unknown[];
  listJobs: (params: { offset: number; limit: number }) => Promise<TJob[]>;
  deleteJob: (jobId: string) => Promise<void>;
  getJobName: (job: TJob) => string;
  formatStage?: (stage: string | null | undefined) => string;
};

function getAnalysisJobBadgeVariant(job: LabJobBase) {
  if (job.status === "failed") return "destructive";
  if (job.status === "succeeded") return "default";
  return "secondary";
}

function LabDashboardPageView<TJob extends LabJobBase>({
  config,
}: {
  config: LabDashboardConfig<TJob>;
}) {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const NewTaskDialog = config.newTaskDialog;

  const providersQuery = useQuery({
    queryKey: providerQueryKeys.lists(),
    queryFn: api.getProviderConfigs,
  });

  const jobsQuery = useQuery({
    queryKey: config.getJobsQueryKey(page),
    queryFn: () =>
      config.listJobs({
        offset: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
  });

  const deleteJobMutation = useMutation({
    mutationFn: config.deleteJob,
    onMutate: async (jobId) => {
      await queryClient.cancelQueries({ queryKey: config.jobsListQueryKey });
      const previousQueries = queryClient.getQueriesData<TJob[]>({
        queryKey: config.jobsListQueryKey,
      });
      for (const [queryKey, data] of previousQueries) {
        if (!Array.isArray(data)) continue;
        queryClient.setQueryData<TJob[]>(
          queryKey,
          data.filter((job) => job.id !== jobId),
        );
      }
      return { previousQueries };
    },
    onSuccess: (_data, jobId) => {
      queryClient.removeQueries({ queryKey: config.getJobDetailQueryKey(jobId) });
      toast.success("分析任务已删除");
    },
    onError: (error, _jobId, context) => {
      if (context?.previousQueries) {
        for (const [queryKey, data] of context.previousQueries) {
          queryClient.setQueryData(queryKey, data);
        }
      }
      toast.error(error instanceof Error ? error.message : "删除失败");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: config.jobsListQueryKey });
    },
  });

  const providers = providersQuery.data ?? [];
  const jobs = jobsQuery.data ?? [];
  const hasNextPage = jobs.length === PAGE_SIZE;

  useEffect(() => {
    if (jobsQuery.isSuccess && jobs.length === 0 && page > 1) {
      setPage((p) => Math.max(1, p - 1));
    }
  }, [jobsQuery.isSuccess, jobs.length, page]);

  if (providersQuery.isLoading || jobsQuery.isLoading) {
    return <PageLoading title={config.loadingTitle} />;
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

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{config.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{config.description}</p>
        </div>
        <NewTaskDialog providers={providers} />
      </div>

      {jobs.length === 0 && page === 1 ? (
        <Card>
          <CardHeader>
            <CardTitle>{config.emptyTitle}</CardTitle>
            <CardDescription>{config.emptyDescription}</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {jobs.map((job) => (
              <Card
                key={job.id}
                className="flex flex-col transition-all hover:ring-2 hover:ring-primary hover:border-transparent cursor-pointer overflow-hidden"
              >
                <CardHeader className="pb-4">
                  <div className="flex items-start justify-between gap-4">
                    <CardTitle className="text-lg leading-tight hover:underline line-clamp-1">
                      <Link href={`${config.detailPathPrefix}/${job.id}`}>{config.getJobName(job)}</Link>
                    </CardTitle>
                    <Badge variant={getAnalysisJobBadgeVariant(job)} className="shrink-0">
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
                    {job.stage ? (
                      <div className="flex justify-between">
                        <span>当前阶段</span>
                        <strong className="font-medium text-foreground text-right">
                          {config.formatStage ? config.formatStage(job.stage) : job.stage}
                        </strong>
                      </div>
                    ) : null}
                  </div>
                </CardContent>
                <CardFooter className="pt-4 border-t bg-muted/20 flex gap-2">
                  <Button variant="secondary" size="sm" className="flex-1" asChild>
                    <Link href={`${config.detailPathPrefix}/${job.id}`}>进入工作台</Link>
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="px-3 text-destructive hover:bg-destructive hover:text-destructive-foreground"
                        disabled={deleteJobMutation.isPending}
                        title="删除任务"
                        onClick={(e) => {
                          e.stopPropagation();
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                    >
                      <AlertDialogHeader>
                        <AlertDialogTitle>确定要删除该分析任务吗？</AlertDialogTitle>
                        <AlertDialogDescription>
                          此操作不可恢复，将永久删除该分析任务及相关数据。
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel onClick={(e) => e.stopPropagation()}>取消</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteJobMutation.mutate(job.id);
                          }}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          删除
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </CardFooter>
              </Card>
            ))}
          </div>

          {jobs.length > 0 || page > 1 ? (
            <Pagination className="mt-8 justify-end">
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      if (page > 1) setPage((p) => p - 1);
                    }}
                    className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>

                <PaginationItem>
                  <PaginationLink href="#" onClick={(e) => e.preventDefault()} isActive>
                    {page}
                  </PaginationLink>
                </PaginationItem>

                <PaginationItem>
                  <PaginationNext
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      if (hasNextPage) setPage((p) => p + 1);
                    }}
                    className={!hasNextPage ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          ) : null}
        </>
      )}
    </section>
  );
}

export function StyleLabDashboardPageView() {
  return (
    <LabDashboardPageView<StyleAnalysisJobListItem>
      config={{
        title: "Style Lab Dashboard",
        description: "管理所有的风格分析任务。点击卡片进入完整分析流程。",
        loadingTitle: "正在载入 Style Lab...",
        emptyTitle: "还没有分析任务",
        emptyDescription: "点击右上角新建任务上传样本。",
        detailPathPrefix: "/style-lab",
        newTaskDialog: StyleLabNewTaskDialog,
        jobsListQueryKey: styleLabQueryKeys.jobs.lists(),
        getJobsQueryKey: styleLabQueryKeys.jobs.list,
        getJobDetailQueryKey: styleLabQueryKeys.jobs.detail,
        listJobs: api.getStyleAnalysisJobs,
        deleteJob: api.deleteStyleAnalysisJob,
        getJobName: (job) => job.profile_style_name ?? job.style_name,
      }}
    />
  );
}

export function PlotLabDashboardPageView() {
  return (
    <LabDashboardPageView<PlotAnalysisJobListItem>
      config={{
        title: "Plot Lab Dashboard",
        description: "管理所有的情节分析任务。点击卡片进入完整分析流程。",
        loadingTitle: "正在载入 Plot Lab...",
        emptyTitle: "还没有分析任务",
        emptyDescription: "点击右上角新建任务上传样本。",
        detailPathPrefix: "/plot-lab",
        newTaskDialog: PlotLabNewTaskDialog,
        jobsListQueryKey: plotLabQueryKeys.jobs.lists(),
        getJobsQueryKey: plotLabQueryKeys.jobs.list,
        getJobDetailQueryKey: plotLabQueryKeys.jobs.detail,
        listJobs: api.getPlotAnalysisJobs,
        deleteJob: api.deletePlotAnalysisJob,
        getJobName: (job) => job.profile_plot_name ?? job.plot_name,
        formatStage: formatPlotStageLabel,
      }}
    />
  );
}
