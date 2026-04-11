"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { PageError, PageLoading } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import {
  STYLE_ANALYSIS_JOB_STATUS,
  type ProviderConfig,
  type StyleAnalysisJobListItem,
} from "@/lib/types";

function getStyleAnalysisJobBadgeVariant(job: StyleAnalysisJobListItem) {
  if (job.status === STYLE_ANALYSIS_JOB_STATUS.FAILED) return "destructive";
  if (job.status === STYLE_ANALYSIS_JOB_STATUS.SUCCEEDED) return "default";
  return "secondary";
}

const createTaskSchema = z.object({
  style_name: z.string().trim().min(1, "请输入风格档案名称"),
  provider_id: z.string().min(1, "请选择 Provider"),
  model: z.string(),
  file: z.custom<File | null>(
    (value) => value instanceof File,
    { message: "请上传 TXT 样本" },
  ),
});

type CreateTaskFormValues = z.infer<typeof createTaskSchema>;

export function StyleLabPageClient() {
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

export function StyleLabNewTaskDialog({ providers }: { providers: ProviderConfig[] }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const form = useForm<CreateTaskFormValues>({
    resolver: zodResolver(createTaskSchema, undefined, { mode: "sync" }),
    defaultValues: {
      style_name: "",
      provider_id: providers[0]?.id ?? "",
      model: "",
      file: null,
    },
  });

  const resetForm = React.useCallback(() => {
    form.reset({
      style_name: "",
      provider_id: providers[0]?.id ?? "",
      model: "",
      file: null,
    });
  }, [form, providers]);

  React.useEffect(() => {
    const selectedProviderId = form.getValues("provider_id");
    if (!selectedProviderId && providers.length > 0) {
      form.setValue("provider_id", providers[0].id, { shouldValidate: true });
    }
  }, [form, providers]);

  const createJobMutation = useMutation({
    mutationFn: api.createStyleAnalysisJob,
    onSuccess: (newJob) => {
      toast.success("分析任务已创建");
      queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs"] });
      setOpen(false);
      resetForm();
      // Redirect to the new wizard page
      router.push(`/style-lab/${newJob.id}`);
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "创建任务失败");
    },
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) {
          resetForm();
        }
      }}
    >
      <DialogTrigger asChild>
        <Button>
          + 新建分析任务
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <form
          onSubmit={form.handleSubmit((values) => {
            createJobMutation.mutate({
              style_name: values.style_name.trim(),
              provider_id: values.provider_id,
              model: values.model.trim() || undefined,
              file: values.file as File,
            });
          })}
        >
          <DialogHeader>
            <DialogTitle>新建分析任务</DialogTitle>
            <DialogDescription>
              上传样本，创建新的风格分析任务。
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="style-name-input">风格档案名称</Label>
              <Input
                id="style-name-input"
                placeholder="例如：金庸武侠风"
                {...form.register("style_name")}
              />
              {form.formState.errors.style_name ? (
                <p className="text-xs text-destructive">{form.formState.errors.style_name.message}</p>
              ) : null}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="style-provider-select">Provider</Label>
              <Controller
                control={form.control}
                name="provider_id"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="style-provider-select">
                      <SelectValue placeholder="选择 Provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {providers.map((provider) => (
                        <SelectItem key={provider.id} value={provider.id}>
                          {provider.label} / {provider.default_model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {form.formState.errors.provider_id ? (
                <p className="text-xs text-destructive">{form.formState.errors.provider_id.message}</p>
              ) : null}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="style-model-override">模型覆盖 (选填)</Label>
              <Input
                id="style-model-override"
                placeholder="留空则使用 Provider 默认模型"
                {...form.register("model")}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="style-sample-file">TXT 样本</Label>
              <Controller
                control={form.control}
                name="file"
                render={({ field }) => (
                  <Input
                    id="style-sample-file"
                    type="file"
                    accept=".txt,text/plain"
                    onChange={(e) => field.onChange(e.target.files?.[0] ?? null)}
                  />
                )}
              />
              {form.formState.errors.file ? (
                <p className="text-xs text-destructive">{form.formState.errors.file.message}</p>
              ) : null}
            </div>
          </div>
          <div className="flex justify-end">
            <Button type="submit" disabled={createJobMutation.isPending}>
              {createJobMutation.isPending ? "创建中..." : "开始分析"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
