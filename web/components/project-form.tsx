"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Check, ChevronsUpDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { Project, ProjectPayload, ProviderConfig, StyleProfileListItem } from "@/lib/types";

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
  providers,
  styleProfiles,
  project,
  submitting,
  onSubmit,
}: {
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  project?: Project;
  submitting: boolean;
  onSubmit: (values: ProjectPayload | Partial<ProjectPayload>) => Promise<void>;
}) {
  const [providerOpen, setProviderOpen] = useState(false);
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
  }, [form, project]);

  return (
    <form
      onSubmit={form.handleSubmit(async (values) => {
        await onSubmit(values);
      })}
    >
      <Card>
        <CardContent className="grid gap-5 pt-6">
          <div className="grid gap-2">
            <Label htmlFor="project-name">项目名称</Label>
            <Input id="project-name" {...form.register("name")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-description">简介</Label>
            <Textarea id="project-description" className="min-h-[120px]" {...form.register("description")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-status">状态</Label>
            <Select
              value={form.watch("status")}
              onValueChange={(val) => form.setValue("status", val as "draft" | "active" | "paused")}
            >
              <SelectTrigger id="project-status" className="bg-background">
                <SelectValue placeholder="选择状态" />
              </SelectTrigger>
              <SelectContent className="border shadow-md rounded-md bg-popover text-popover-foreground">
                <SelectItem value="draft" className="cursor-pointer">draft</SelectItem>
                <SelectItem value="active" className="cursor-pointer">active</SelectItem>
                <SelectItem value="paused" className="cursor-pointer">paused</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-provider">默认 Provider</Label>
            <Popover open={providerOpen} onOpenChange={setProviderOpen}>
              <PopoverTrigger asChild>
                <Button
                  id="project-provider"
                  variant="outline"
                  role="combobox"
                  className="w-full justify-between font-normal bg-background hover:bg-accent hover:text-accent-foreground data-[state=open]:bg-accent h-10 px-3 py-2 text-sm border-input"
                >
                  <span className="truncate">
                    {form.watch("default_provider_id")
                      ? (() => {
                          const selected = providers.find((p) => p.id === form.watch("default_provider_id"));
                          return selected ? `${selected.label} / ${selected.default_model}` : "选择 Provider";
                        })()
                      : "选择 Provider"}
                  </span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50 transition-transform duration-200" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-full p-0 border shadow-md rounded-md" align="start" style={{ width: "var(--radix-popover-trigger-width)" }}>
                <Command className="bg-popover text-popover-foreground">
                  <CommandInput placeholder="搜索 Provider..." className="border-none focus:ring-0" />
                  <CommandList>
                    <CommandEmpty>未找到对应的 Provider</CommandEmpty>
                    <CommandGroup>
                      {providers.map((provider) => (
                        <CommandItem
                          key={provider.id}
                          value={`${provider.label} ${provider.default_model}`}
                          onSelect={() => {
                            form.setValue("default_provider_id", provider.id);
                            setProviderOpen(false);
                          }}
                          className="cursor-pointer"
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              form.watch("default_provider_id") === provider.id ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {provider.label}
                          <span className="ml-2 text-foreground/70 truncate">/ {provider.default_model}</span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-model">项目默认模型</Label>
            <Input id="project-model" placeholder="留空则回退到 Provider 默认模型" {...form.register("default_model")} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-style-profile">风格档案</Label>
            <Select
              value={form.watch("style_profile_id") ?? "__none__"}
              onValueChange={(val) => form.setValue("style_profile_id", val === "__none__" ? null : val)}
            >
              <SelectTrigger id="project-style-profile" aria-label="风格档案" className="bg-background">
                <SelectValue placeholder="选择风格档案" />
              </SelectTrigger>
              <SelectContent className="border shadow-md rounded-md bg-popover text-popover-foreground">
                <SelectItem value="__none__" className="cursor-pointer">未挂载</SelectItem>
                {styleProfiles.map((profile) => (
                  <SelectItem key={profile.id} value={profile.id} className="cursor-pointer">
                    {profile.style_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3 mt-6 pt-6 border-t">
        <Button asChild variant="outline">
          <Link href="/projects">取消</Link>
        </Button>
        <Button type="submit" disabled={submitting}>
          保存项目
        </Button>
      </div>
    </form>
  );
}
