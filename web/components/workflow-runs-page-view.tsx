"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, RotateCcw, Trash2 } from "lucide-react";
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import type { NovelWorkflowCreatePayload, NovelWorkflowListItem } from "@/lib/types";
import {
  WORKFLOW_RUNS_ALL_FILTER,
  WORKFLOW_RUNS_PAGE_SIZE,
  workflowRunsQueryKeys,
  type WorkflowRunsIntentFilter,
  type WorkflowRunsStatusFilter,
} from "@/lib/workflow-runs-query-keys";
import { projectsQueryKeys } from "@/lib/projects-query-keys";
import {
  formatWorkflowDate,
  WORKFLOW_INTENT_LABELS,
  WORKFLOW_STATUS_LABELS,
} from "@/lib/workflow-run-labels";

type IntentType = NovelWorkflowCreatePayload["intent_type"];
type StatusType = NovelWorkflowListItem["status"];

export function WorkflowRunsPageView() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [projectId, setProjectId] = useState(WORKFLOW_RUNS_ALL_FILTER);
  const [intentType, setIntentType] = useState<WorkflowRunsIntentFilter>(WORKFLOW_RUNS_ALL_FILTER);
  const [status, setStatus] = useState<WorkflowRunsStatusFilter>(WORKFLOW_RUNS_ALL_FILTER);

  const runsQuery = useQuery({
    queryKey: workflowRunsQueryKeys.list(projectId, intentType, status, page),
    queryFn: () =>
      api.listNovelWorkflows({
        projectId: projectId === WORKFLOW_RUNS_ALL_FILTER ? null : projectId,
        intentType: intentType === WORKFLOW_RUNS_ALL_FILTER ? null : intentType,
        status: status === WORKFLOW_RUNS_ALL_FILTER ? null : status,
        offset: (page - 1) * WORKFLOW_RUNS_PAGE_SIZE,
        limit: WORKFLOW_RUNS_PAGE_SIZE,
      }),
    refetchInterval: (query) =>
      query.state.data?.some(
        (run) => run.status === "pending" || run.status === "running",
      )
        ? 1000
        : false,
    staleTime: 30_000,
  });

  const projectsQuery = useQuery({
    queryKey: projectsQueryKeys.workflowFilter(),
    queryFn: () => api.getProjects({ includeArchived: true, offset: 0, limit: 100 }),
    staleTime: 30_000,
  });

  const clearHistoryMutation = useMutation({
    mutationFn: api.clearNovelWorkflowHistory,
    onSuccess: () => {
      setPage(1);
      queryClient.removeQueries({ queryKey: ["novel-workflows"] });
      toast.success("运行历史已清空");
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "清空失败");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["novel-workflows"] });
    },
  });

  const hasNextPage = (runsQuery.data?.length ?? 0) === WORKFLOW_RUNS_PAGE_SIZE;
  const intents = useMemo(
    () => Object.keys(WORKFLOW_INTENT_LABELS) as IntentType[],
    [],
  );
  const statuses = useMemo(
    () => Object.keys(WORKFLOW_STATUS_LABELS) as StatusType[],
    [],
  );

  if (runsQuery.isLoading) {
    return <PageLoading title="正在加载运行历史..." />;
  }

  if (runsQuery.isError || !runsQuery.data) {
    return (
      <PageError
        title="运行历史加载失败"
        message={runsQuery.error instanceof Error ? runsQuery.error.message : "请重试"}
      />
    );
  }

  const resetFilters = () => {
    setProjectId(WORKFLOW_RUNS_ALL_FILTER);
    setIntentType(WORKFLOW_RUNS_ALL_FILTER);
    setStatus(WORKFLOW_RUNS_ALL_FILTER);
    setPage(1);
  };

  return (
    <section className="motion-page space-y-6">
      <div className="animate-slide-up flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">运行历史</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            查看 Novel Workflow 的执行记录、日志、请求载荷与 Prompt Trace。
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[220px_180px_160px_auto_auto]">
          <Select
            value={projectId}
            onValueChange={(value) => {
              setProjectId(value);
              setPage(1);
            }}
          >
            <SelectTrigger aria-label="按项目过滤">
              <SelectValue placeholder="全部项目" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={WORKFLOW_RUNS_ALL_FILTER}>全部项目</SelectItem>
              {(projectsQuery.data ?? []).map((project) => (
                <SelectItem key={project.id} value={project.id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={intentType}
            onValueChange={(value) => {
              setIntentType(value as WorkflowRunsIntentFilter);
              setPage(1);
            }}
          >
            <SelectTrigger aria-label="按任务类型过滤">
              <SelectValue placeholder="全部类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={WORKFLOW_RUNS_ALL_FILTER}>全部类型</SelectItem>
              {intents.map((intent) => (
                <SelectItem key={intent} value={intent}>
                  {WORKFLOW_INTENT_LABELS[intent]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={status}
            onValueChange={(value) => {
              setStatus(value as WorkflowRunsStatusFilter);
              setPage(1);
            }}
          >
            <SelectTrigger aria-label="按状态过滤">
              <SelectValue placeholder="全部状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={WORKFLOW_RUNS_ALL_FILTER}>全部状态</SelectItem>
              {statuses.map((item) => (
                <SelectItem key={item} value={item}>
                  {WORKFLOW_STATUS_LABELS[item]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button variant="outline" onClick={resetFilters} className="gap-2">
            <RotateCcw className="h-4 w-4" />
            重置
          </Button>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                className="gap-2 text-destructive hover:bg-destructive hover:text-destructive-foreground"
                disabled={clearHistoryMutation.isPending || runsQuery.data.length === 0}
              >
                <Trash2 className="h-4 w-4" />
                清空
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>确定要清空运行历史吗？</AlertDialogTitle>
                <AlertDialogDescription>
                  此操作不可恢复，将永久删除所有已完成或失败的运行记录、日志与 Prompt Trace。
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>取消</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => clearHistoryMutation.mutate()}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  清空
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <Card className="animate-scale-in motion-delay-1">
        <CardHeader>
          <CardTitle className="text-lg">Workflow Runs</CardTitle>
          <CardDescription>Prompt Trace 保存在每条 run 的 artifact 中。</CardDescription>
        </CardHeader>
        <CardContent>
          {runsQuery.data.length === 0 ? (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              暂无运行记录。
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-sm">
                <thead className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="py-3 pr-4 font-medium">任务</th>
                    <th className="py-3 pr-4 font-medium">状态</th>
                    <th className="py-3 pr-4 font-medium">项目 / 章节</th>
                    <th className="py-3 pr-4 font-medium">模型</th>
                    <th className="py-3 pr-4 font-medium">创建 / 完成</th>
                    <th className="py-3 text-right font-medium">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {runsQuery.data.map((run) => (
                    <tr key={run.id} className="motion-row align-top">
                      <td className="py-4 pr-4">
                        <div className="font-medium text-foreground">
                          {WORKFLOW_INTENT_LABELS[run.intent_type]}
                        </div>
                        <div className="mt-1 font-mono text-xs text-muted-foreground">{run.id}</div>
                      </td>
                      <td className="py-4 pr-4">
                        <StatusBadge status={run.status} />
                        {run.stage ? (
                          <div className="mt-1 text-xs text-muted-foreground">{run.stage}</div>
                        ) : null}
                      </td>
                      <td className="py-4 pr-4">
                        <div>{run.project_name || run.project_id || "无项目"}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {run.chapter_title || run.chapter_id || "无章节"}
                        </div>
                      </td>
                      <td className="py-4 pr-4">
                        <div>{run.provider_label || run.provider_id || "未知 Provider"}</div>
                        <div className="mt-1 text-xs text-muted-foreground">{run.model_name || "-"}</div>
                      </td>
                      <td className="py-4 pr-4">
                        <div>{formatWorkflowDate(run.created_at)}</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {formatWorkflowDate(run.completed_at)}
                        </div>
                      </td>
                      <td className="py-4 text-right">
                        <Button asChild variant="outline" size="sm" className="gap-2">
                          <Link href={`/workflow-runs/${run.id}`}>
                            <Eye className="h-4 w-4" />
                            查看 Trace
                          </Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Pagination className="justify-end animate-fade-in motion-delay-2">
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious
              href="#"
              onClick={(event) => {
                event.preventDefault();
                if (page > 1) setPage(page - 1);
              }}
              className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
            />
          </PaginationItem>
          <PaginationItem>
            <PaginationLink href="#" onClick={(event) => event.preventDefault()} isActive>
              {page}
            </PaginationLink>
          </PaginationItem>
          <PaginationItem>
            <PaginationNext
              href="#"
              onClick={(event) => {
                event.preventDefault();
                if (hasNextPage) setPage(page + 1);
              }}
              className={!hasNextPage ? "pointer-events-none opacity-50" : "cursor-pointer"}
            />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </section>
  );
}

function StatusBadge({ status }: { status: StatusType }) {
  const variant = status === "failed" ? "destructive" : status === "succeeded" ? "secondary" : "outline";
  return <Badge variant={variant}>{WORKFLOW_STATUS_LABELS[status]}</Badge>;
}
