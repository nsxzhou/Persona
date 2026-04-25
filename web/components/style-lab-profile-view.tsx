"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { type UseFormReturn } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { type StyleAnalysisJob, type StyleProfile } from "@/lib/types";
import { type FormValues } from "@/lib/validations/style-lab";

export function StyleLabProfileView({
  job,
  profile,
  isEditing,
  onEditStart,
  onEditCancel,
  onSave,
  saving,
  form,
}: {
  job: StyleAnalysisJob;
  profile: StyleProfile;
  isEditing: boolean;
  onEditStart: () => void;
  onEditCancel: () => void;
  onSave: () => void;
  saving: boolean;
  form: UseFormReturn<FormValues>;
}) {
  const [activeTab, setActiveTab] = React.useState("summary");
  const styleNameField = form.register("styleName");
  const voiceProfileField = form.register("voiceProfileMarkdown");

  React.useEffect(() => {
    if (isEditing) {
      form.reset({
        styleName: profile.style_name,
        voiceProfileMarkdown: profile.voice_profile_markdown,
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
      {/* 导航栏 */}
      <nav className="sticky top-0 bg-background/90 backdrop-blur-md border-b border-border px-6 py-4 flex justify-between items-center z-10">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild className="h-8 w-8 text-muted-foreground hover:text-foreground">
            <Link href="/style-lab"><ArrowLeft className="h-4 w-4" /></Link>
          </Button>
          <div className="text-xs font-bold tracking-widest text-muted-foreground uppercase flex items-center gap-2">
            Style Lab <span className="font-normal text-border">/</span> Profile
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
        {/* 标题区 */}
        <header className="mb-12 text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-tight tracking-wide font-[family:var(--font-prose)] text-foreground">
            {isEditing ? (
              <span className="text-muted-foreground text-2xl">正在编辑风格档案...</span>
            ) : (
              profile.style_name
            )}
          </h1>
          <div className="flex items-center justify-center gap-3 text-sm text-muted-foreground">
            <Badge variant="secondary" className="font-mono">{job.model_name}</Badge>
            <Badge variant="outline" className="font-mono truncate max-w-[200px]" title={job.sample_file.original_filename}>
              {job.sample_file.original_filename}
            </Badge>
          </div>
        </header>

        {/* 使用 Tabs 重构文章主体 */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="flex justify-center mb-8">
            <TabsList className="bg-transparent border-b border-border rounded-none p-0 h-auto space-x-6">
              <TabsTrigger 
                value="summary" 
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-2 py-3 text-base font-medium text-muted-foreground data-[state=active]:text-foreground"
              >
                Voice Profile
              </TabsTrigger>
              <TabsTrigger 
                value="report" 
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-2 py-3 text-base font-medium text-muted-foreground data-[state=active]:text-foreground"
              >
                原始分析报告
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="mt-8">
            <TabsContent value="summary" className="focus-visible:outline-none">
              {isEditing ? (
                <div className="space-y-6 max-w-3xl mx-auto">
                  <div className="grid gap-2">
                    <Label htmlFor="style-name">风格名称</Label>
                    <Input id="style-name" {...styleNameField} />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="voice-profile-markdown">Voice Profile Markdown</Label>
                    <Textarea
                      id="voice-profile-markdown"
                      aria-label="Voice Profile Markdown"
                      className="min-h-[300px] font-mono text-sm leading-relaxed"
                      {...voiceProfileField}
                      onChange={(e) => {
                        voiceProfileField.onChange(e);
                        adjustHeight(e);
                      }}
                    />
                  </div>
                </div>
              ) : (
                <div className="whitespace-pre-wrap leading-loose text-lg text-foreground/90 font-[family:var(--font-prose)] text-justify max-w-3xl mx-auto">
                  {profile.voice_profile_markdown || "暂无 Voice Profile"}
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
