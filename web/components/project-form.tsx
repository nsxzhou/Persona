"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { Project, ProjectPayload, ProviderConfig } from "@/lib/types";

const schema = z.object({
  name: z.string().min(1),
  description: z.string(),
  status: z.enum(["draft", "active", "paused"]),
  default_provider_id: z.string().min(1),
  default_model: z.string().optional(),
  style_profile_id: z.string().nullable(),
});

type FormValues = z.infer<typeof schema>;

export function ProjectForm({
  title,
  description,
  providers,
  project,
  submitting,
  onSubmit,
}: {
  title: string;
  description: string;
  providers: ProviderConfig[];
  project?: Project;
  submitting: boolean;
  onSubmit: (values: ProjectPayload | Partial<ProjectPayload>) => Promise<void>;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema, undefined, { mode: "sync" }),
    defaultValues: {
      name: "",
      description: "",
      status: "draft",
      default_provider_id: "",
      default_model: "",
      style_profile_id: null,
    },
  });

  useEffect(() => {
    form.reset({
      name: project?.name ?? "",
      description: project?.description ?? "",
      status: project?.status ?? "draft",
      default_provider_id: project?.provider.id ?? providers[0]?.id ?? "",
      default_model: project?.default_model ?? "",
      style_profile_id: project?.style_profile_id ?? null,
    });
  }, [form, project, providers]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-5" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="grid gap-2">
            <Label htmlFor="project-name">项目名称</Label>
            <Input id="project-name" {...form.register("name")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-description">简介</Label>
            <Textarea id="project-description" {...form.register("description")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-status">状态</Label>
            <select
              id="project-status"
              className="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              {...form.register("status")}
            >
              <option value="draft">draft</option>
              <option value="active">active</option>
              <option value="paused">paused</option>
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-provider">默认 Provider</Label>
            <select
              id="project-provider"
              className="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              {...form.register("default_provider_id")}
            >
              {providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.label} / {provider.default_model}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-model">项目默认模型</Label>
            <Input id="project-model" placeholder="留空则回退到 Provider 默认模型" {...form.register("default_model")} />
          </div>
          <div className="flex gap-3">
            <Button type="submit" disabled={submitting}>
              保存项目
            </Button>
            <Button asChild variant="outline">
              <Link href="/projects">返回列表</Link>
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}