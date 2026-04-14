"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";
import { Controller, useForm } from "react-hook-form";
import { UploadCloud, FileText, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
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
import type { ProviderConfig } from "@/lib/types";

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

const formatBytes = (bytes: number, decimals = 2) => {
  if (!+bytes) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

export function StyleLabNewTaskDialog({ providers }: { providers: ProviderConfig[] }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const enabledProviders = React.useMemo(
    () => providers.filter((provider) => provider.is_enabled),
    [providers],
  );
  const form = useForm<CreateTaskFormValues>({
    resolver: zodResolver(createTaskSchema, undefined, { mode: "sync" }),
    defaultValues: {
      style_name: "",
      provider_id: enabledProviders[0]?.id ?? "",
      model: "",
      file: null,
    },
  });

  const resetForm = React.useCallback(() => {
    form.reset({
      style_name: "",
      provider_id: enabledProviders[0]?.id ?? "",
      model: "",
      file: null,
    });
  }, [enabledProviders, form]);

  React.useEffect(() => {
    const selectedProviderId = form.getValues("provider_id");
    const selectedProvider = providers.find((provider) => provider.id === selectedProviderId);
    if (!selectedProviderId && enabledProviders.length > 0) {
      form.setValue("provider_id", enabledProviders[0].id, { shouldValidate: true });
      return;
    }
    if (selectedProviderId && selectedProvider && !selectedProvider.is_enabled) {
      form.setValue("provider_id", enabledProviders[0]?.id ?? "", { shouldValidate: true });
    }
  }, [enabledProviders, form, providers]);

  const selectedProviderId = form.watch("provider_id");
  const selectedProvider = React.useMemo(
    () => providers.find((provider) => provider.id === selectedProviderId),
    [providers, selectedProviderId],
  );
  const canSubmit = Boolean(selectedProvider?.is_enabled) && enabledProviders.length > 0;

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
      toast.error(error instanceof Error ? error.message : "未知错误");
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
            const provider = providers.find((item) => item.id === values.provider_id);
            if (!provider?.is_enabled) {
              toast.error("当前 Provider 已被禁用，请先在模型配置中启用");
              return;
            }
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
                        <SelectItem
                          key={provider.id}
                          value={provider.id}
                          disabled={!provider.is_enabled}
                        >
                          {provider.label} / {provider.default_model}
                          {provider.is_enabled ? "" : "（已禁用）"}
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
                  <div className="space-y-2">
                    {!field.value ? (
                      <div className="relative group flex flex-col items-center justify-center w-full h-32 rounded-lg border-2 border-dashed border-muted-foreground/25 bg-muted/20 transition-all hover:bg-muted/40 hover:border-primary/50 cursor-pointer overflow-hidden">
                        <input
                          id="style-sample-file"
                          type="file"
                          accept=".txt,text/plain"
                          onChange={(e) => field.onChange(e.target.files?.[0] ?? null)}
                          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                        />
                        <div className="flex flex-col items-center justify-center space-y-2 text-center px-4">
                          <div className="p-2 bg-background/50 rounded-full shadow-sm border border-border group-hover:scale-105 group-hover:text-primary transition-all duration-200">
                            <UploadCloud className="w-5 h-5 text-muted-foreground group-hover:text-primary" />
                          </div>
                          <div className="text-sm font-medium">
                            <span className="text-primary hover:underline">点击上传</span> 或拖拽文件
                          </div>
                          <p className="text-xs text-muted-foreground">支持 .txt 格式</p>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-muted/30 shadow-sm transition-all">
                        <div className="flex items-center space-x-3 overflow-hidden">
                          <div className="p-2 bg-primary/10 text-primary rounded-md shrink-0">
                            <FileText className="w-5 h-5" />
                          </div>
                          <div className="flex flex-col overflow-hidden">
                            <span className="text-sm font-medium truncate">{field.value.name}</span>
                            <span className="text-xs text-muted-foreground">{formatBytes(field.value.size)}</span>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => field.onChange(null)}
                          className="p-2 text-muted-foreground hover:text-destructive transition-colors shrink-0 rounded-md hover:bg-muted"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                )}
              />
              {form.formState.errors.file ? (
                <p className="text-xs text-destructive">{form.formState.errors.file.message}</p>
              ) : null}
            </div>
          </div>
          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={createJobMutation.isPending || !canSubmit}
            >
              {createJobMutation.isPending ? "创建中..." : "开始分析"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
