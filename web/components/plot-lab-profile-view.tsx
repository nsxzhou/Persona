"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { type UseFormReturn } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MarkdownEditorField } from "@/components/markdown-editor-field";
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

  React.useEffect(() => {
    if (isEditing) {
      form.reset({
        plotName: profile.plot_name,
        plotSkeletonMarkdown: profile.plot_skeleton_markdown ?? "",
        storyEngineMarkdown: profile.story_engine_markdown,
      });
    }
  }, [isEditing, profile, form]);

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

      <main className="max-w-5xl mx-auto py-12 px-6">
        <header className="mb-12 text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight tracking-wide font-[family:var(--font-prose)] text-foreground">
            {profile.plot_name}
            {isEditing && (
              <Badge variant="secondary" className="ml-3 text-orange-600 bg-orange-50 border-orange-200 align-middle text-sm font-medium">
                编辑中
              </Badge>
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
                Story Engine
              </TabsTrigger>
              <TabsTrigger value="skeleton" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-2 py-3 text-base font-medium text-muted-foreground data-[state=active]:text-foreground">
                全书骨架
              </TabsTrigger>
              <TabsTrigger value="report" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-2 py-3 text-base font-medium text-muted-foreground data-[state=active]:text-foreground">
                原始分析报告
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="mt-8">
            <TabsContent value="summary" className="focus-visible:outline-none">
              {isEditing ? (
                <div className="space-y-6 max-w-4xl mx-auto">
                  <Card>
                    <CardHeader>
                      <CardTitle>编辑情节档案</CardTitle>
                      <CardDescription>修改情节档案的名称和 Story Engine 内容。</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-8">
                      <div className="grid gap-2">
                        <Label htmlFor="plot-name">情节档案名称</Label>
                        <Input id="plot-name" placeholder="为此情节档案命名" {...plotNameField} />
                      </div>
                      <MarkdownEditorField<FormValues>
                        control={form.control}
                        name="storyEngineMarkdown"
                        id="story-engine-markdown"
                        label="Story Engine Markdown"
                        minHeight={520}
                      />
                      <div className="flex justify-end gap-3 pt-4 border-t">
                        <Button variant="ghost" onClick={onEditCancel} disabled={saving}>
                          取消
                        </Button>
                        <Button onClick={onSave} disabled={saving}>
                          {saving ? "保存中..." : "保存修改"}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <div className="whitespace-pre-wrap leading-loose text-lg text-foreground/90 font-[family:var(--font-prose)] text-justify max-w-4xl mx-auto">
                  {profile.story_engine_markdown || "暂无 Story Engine"}
                </div>
              )}
            </TabsContent>

            <TabsContent value="skeleton" className="focus-visible:outline-none max-w-4xl mx-auto">
              {isEditing ? (
                <div className="space-y-6">
                  <MarkdownEditorField<FormValues>
                    control={form.control}
                    name="plotSkeletonMarkdown"
                    id="plot-skeleton-markdown"
                    label="全书骨架 Markdown"
                    minHeight={400}
                  />
                </div>
              ) : (
                <div className="bg-muted/10 p-8 rounded-xl border border-border/30 text-base text-foreground/80 leading-relaxed whitespace-pre-wrap font-[family:var(--font-prose)]">
                  {profile.plot_skeleton_markdown || "暂无骨架"}
                </div>
              )}
            </TabsContent>

            <TabsContent value="report" className="focus-visible:outline-none max-w-4xl mx-auto">
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
