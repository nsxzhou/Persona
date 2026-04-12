"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
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
import { api } from "@/lib/api";
import {
  STYLE_ANALYSIS_JOB_STATUS,
  type StyleAnalysisJobListItem,
} from "@/lib/types";
import { StyleLabNewTaskDialog } from "@/components/style-lab-new-task-dialog";

const PAGE_SIZE = 12; // 卡片布局适合 3x4 或者 4x3 的数量

function getStyleAnalysisJobBadgeVariant(job: StyleAnalysisJobListItem) {
  if (job.status === STYLE_ANALYSIS_JOB_STATUS.FAILED) return "destructive";
  if (job.status === STYLE_ANALYSIS_JOB_STATUS.SUCCEEDED) return "default";
  return "secondary";
}

export default function StyleLabPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const providersQuery = useQuery({
    queryKey: ["provider-configs"],
    queryFn: api.getProviderConfigs,
  });

  const jobsQuery = useQuery({
    queryKey: ["style-analysis-jobs", page],
    queryFn: () => api.getStyleAnalysisJobs({ 
      offset: (page - 1) * PAGE_SIZE,
      limit: PAGE_SIZE 
    }),
  });

  const deleteJobMutation = useMutation({
    mutationFn: api.deleteStyleAnalysisJob,
    onSuccess: () => {
      toast.success("分析任务已删除");
      queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs"] });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "删除失败");
    },
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
  const hasNextPage = jobs.length === PAGE_SIZE;

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

      {jobs.length === 0 && page === 1 ? (
        <Card>
          <CardHeader>
            <CardTitle>还没有分析任务</CardTitle>
            <CardDescription>点击右上角新建任务上传样本。</CardDescription>
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
                      <Link href={`/style-lab/${job.id}`}>{job.style_name}</Link>
                    </CardTitle>
                    <Badge variant={getStyleAnalysisJobBadgeVariant(job)} className="shrink-0">
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
                        <strong className="font-medium text-foreground text-right">{job.stage}</strong>
                      </div>
                    ) : null}
                  </div>
                </CardContent>
                <CardFooter className="pt-4 border-t bg-muted/20 flex gap-2">
                  <Button variant="secondary" size="sm" className="flex-1" asChild>
                    <Link href={`/style-lab/${job.id}`}>进入工作台</Link>
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
                    <AlertDialogContent onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                    }}>
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
                            e.preventDefault();
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

          {/* Pagination (Standard) */}
          {jobs.length > 0 || page > 1 ? (
            <Pagination className="mt-8 justify-end">
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious 
                    href="#" 
                    onClick={(e) => {
                      e.preventDefault();
                      if (page > 1) setPage(p => p - 1);
                    }}
                    className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
                
                <PaginationItem>
                  <PaginationLink 
                    href="#" 
                    onClick={(e) => e.preventDefault()}
                    isActive
                  >
                    {page}
                  </PaginationLink>
                </PaginationItem>
                
                <PaginationItem>
                  <PaginationNext 
                    href="#" 
                    onClick={(e) => {
                      e.preventDefault();
                      if (hasNextPage) setPage(p => p + 1);
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