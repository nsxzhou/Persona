"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

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

export function StyleLabNewTaskDialog({ providers }: { providers: ProviderConfig[] }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [styleNameInput, setStyleNameInput] = React.useState("");
  const [selectedProviderId, setSelectedProviderId] = React.useState("");
  const [modelOverride, setModelOverride] = React.useState("");
  const [sampleFile, setSampleFile] = React.useState<File | null>(null);

  React.useEffect(() => {
    if (!selectedProviderId && providers?.length) {
      setSelectedProviderId(providers[0].id);
    }
  }, [providers, selectedProviderId]);

  const createJobMutation = useMutation({
    mutationFn: async () => {
      if (!styleNameInput.trim()) throw new Error("请输入风格档案名称");
      if (!selectedProviderId) throw new Error("请选择 Provider");
      if (!sampleFile) throw new Error("请上传 TXT 样本");

      return api.createStyleAnalysisJob({
        style_name: styleNameInput.trim(),
        provider_id: selectedProviderId,
        model: modelOverride.trim() || undefined,
        file: sampleFile,
      });
    },
    onSuccess: (newJob) => {
      toast.success("分析任务已创建");
      queryClient.invalidateQueries({ queryKey: ["style-analysis-jobs"] });
      setOpen(false);
      // Redirect to the new wizard page
      router.push(`/style-lab/${newJob.id}`);
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "创建任务失败");
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          + 新建分析任务
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
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
              value={styleNameInput}
              onChange={(e) => setStyleNameInput(e.target.value)}
              placeholder="例如：金庸武侠风"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="style-provider-select">Provider</Label>
            <Select value={selectedProviderId} onValueChange={setSelectedProviderId}>
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
          </div>
          <div className="grid gap-2">
            <Label htmlFor="style-model-override">模型覆盖 (选填)</Label>
            <Input
              id="style-model-override"
              value={modelOverride}
              onChange={(e) => setModelOverride(e.target.value)}
              placeholder="留空则使用 Provider 默认模型"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="style-sample-file">TXT 样本</Label>
            <Input
              id="style-sample-file"
              type="file"
              accept=".txt,text/plain"
              onChange={(e) => setSampleFile(e.target.files?.[0] ?? null)}
            />
          </div>
        </div>
        <div className="flex justify-end">
          <Button
            onClick={() => createJobMutation.mutate()}
            disabled={createJobMutation.isPending}
          >
            {createJobMutation.isPending ? "创建中..." : "开始分析"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
