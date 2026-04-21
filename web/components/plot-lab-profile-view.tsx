"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, Copy } from "lucide-react";
import { toast } from "sonner";
import { type UseFormReturn } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { type PlotAnalysisJob, type PlotProfile } from "@/lib/types";
import { type FormValues } from "@/lib/validations/plot-lab";

export function PlotLabProfileView({
  job,
  profile,
  isEditing,
  onEditStart,
  onEditCancel,
  onSave,
  saving,
  form,
}: {
  job: PlotAnalysisJob;
  profile: PlotProfile;
  isEditing: boolean;
  onEditStart: () => void;
  onEditCancel: () => void;
  onSave: () => void;
  saving: boolean;
  form: UseFormReturn<FormValues>;
}) {
  const [activeTab, setActiveTab] = React.useState("summary");
  const plotNameField = form.register("plotName");
  const plotSummaryField = form.register("plotSummaryMarkdown");
  const promptPackField = form.register("promptPackMarkdown");

  React.useEffect(() => {
    if (isEditing) {
      form.reset({
        plotName: profile.plot_name,
        plotSummaryMarkdown: profile.plot_summary_markdown,
        promptPackMarkdown: profile.prompt_pack_markdown,
      });
    }
  }, [isEditing, profile, form]);

  const adjustHeight = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const target = e.target;
    target.style.height = "auto";
    target.style.height = `${Math.max(300, target.scrollHeight)}px`;
  };

  return (
    <div className="-m-8 min-h-screen bg-background text-foreground pb-24 selection:bg-muted">
      <nav className="sticky top-0 bg-background/90 backdrop-blur-md border-b border-border px-6 py-4 flex justify-between items-center z-10">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <Link href="/plot-lab"><ArrowLeft className="h-4 w-4" /></Link>
          </Button>
          <div className="text-xs font-bold tracking-widest text-muted-foreground uppercase flex items-center gap-2">
            Plot Lab <span className="font-normal text-border">/</span> Profile
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          {isEditing ? (
            <>
              <Button variant="ghost" size="sm" onClick={onEditCancel} disabled={saving}>
                取消
              </Button>
              <Button size="sm" onClick={onSave} disabled={saving}>
                {saving ? "保存中..." : "保存修改"}
              </Button>
            </>
          ) : (
            <>
              <span className="text-muted-foreground flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                已保存
              </span>
              <Button variant="ghost" size="sm" onClick={onEditStart} className="text-muted-foreground hover:text-foreground">
                编辑档案
              </Button>
            </>
          )}
        </div>
      </nav>

      <main className="max-w-4xl mx-auto py-12 px-6">
        <header className="mb-12 text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight tracking-wide font-[family:var(--font-prose)] text-foreground">
            {isEditing ? (
              <span className="text-muted-foreground text-2xl">正在编辑情节档案...</span>
            ) : (
              profile.plot_name
            )}
          </h1>
          <div className="flex items-center justify-center gap-3 text-sm text-muted-foreground">
            <Badge variant="secondary" className="font-mono">{job.model_name}</Badge>
            <Badge variant="outline" className="font-mono truncate max-w-[200px]" title={job.sample_file.original_filename}>
              {job.sample_file.original_filename}
            </Badge>
          </div>
        </header>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="flex justify-center mb-8">
            <TabsList className="bg-transparent border-b border-border rounded-none p-0 h-auto space-x-6">
              <TabsTrigger value="summary" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-2 py-3 text-base font-medium text-muted-foreground data-[state=active]:text-foreground">
                剧情摘要
              </TabsTrigger>
              <TabsTrigger value="prompt" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-2 py-3 text-base font-medium text-muted-foreground data-[state=active]:text-foreground">
                提示词资产
              </TabsTrigger>
              <TabsTrigger value="report" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-2 py-3 text-base font-medium text-muted-foreground data-[state=active]:text-foreground">
                原始分析报告
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="mt-8">
            <TabsContent value="summary" className="focus-visible:outline-none">
              {isEditing ? (
                <div className="space-y-6 max-w-3xl mx-auto">
                  <div className="grid gap-2">
                    <Label htmlFor="plot-name">情节档案名称</Label>
                    <Input id="plot-name" {...plotNameField} />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="plot-summary-markdown">剧情摘要 Markdown</Label>
                    <Textarea
                      id="plot-summary-markdown"
                      aria-label="剧情摘要 Markdown"
                      className="min-h-[300px] font-mono text-sm leading-relaxed"
                      {...plotSummaryField}
                      onChange={(e) => {
                        plotSummaryField.onChange(e);
                        adjustHeight(e);
                      }}
                    />
                  </div>
                </div>
              ) : (
                <div className="whitespace-pre-wrap leading-loose text-lg text-foreground/90 font-[family:var(--font-prose)] text-justify max-w-3xl mx-auto">
                  {profile.plot_summary_markdown || "暂无摘要"}
                </div>
              )}
            </TabsContent>

            <TabsContent value="prompt" className="focus-visible:outline-none max-w-3xl mx-auto">
              {isEditing ? (
                <div className="space-y-6">
                  <div className="grid gap-2">
                    <Label htmlFor="prompt-pack-markdown">Prompt Pack Markdown</Label>
                    <Textarea
                      id="prompt-pack-markdown"
                      aria-label="Prompt Pack Markdown"
                      className="min-h-[400px] font-mono text-sm leading-relaxed bg-muted/30"
                      {...promptPackField}
                      onChange={(e) => {
                        promptPackField.onChange(e);
                        adjustHeight(e);
                      }}
                    />
                  </div>
                </div>
              ) : (
                <div className="bg-muted/30 p-8 rounded-xl font-mono text-sm leading-relaxed text-foreground shadow-sm relative group border border-border/50">
                  <Button
                    variant="outline"
                    size="sm"
                    className="absolute top-4 right-4 h-8 text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity bg-background"
                    onClick={() => {
                      navigator.clipboard.writeText(profile.prompt_pack_markdown || "");
                      toast.success("已复制提示词");
                    }}
                  >
                    <Copy className="w-3 h-3 mr-2" /> COPY
                  </Button>
                  <span className="text-muted-foreground block mb-6 select-none border-b border-border/50 pb-2">/* Plot Prompt */</span>
                  <div className="whitespace-pre-wrap">{profile.prompt_pack_markdown || "暂无提示词"}</div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="report" className="focus-visible:outline-none max-w-3xl mx-auto">
              <div className="bg-muted/10 p-8 rounded-xl border border-border/30 text-base text-foreground/80 leading-relaxed whitespace-pre-wrap font-[family:var(--font-prose)]">
                {profile.analysis_report_markdown || "暂无报告"}
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </main>
    </div>
  );
}
