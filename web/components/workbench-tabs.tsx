"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Settings } from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BibleTabContent } from "@/components/bible-tab-content";
import { SettingsTab } from "@/components/settings-tab";
import { api } from "@/lib/api";
import {
  AI_ENABLED_SECTIONS,
  BIBLE_SECTION_META,
  RECOMMENDED_PREREQUISITES,
  type BibleFieldKey,
} from "@/lib/bible-fields";
import type { Project, ProviderConfig, StyleProfileListItem } from "@/lib/types";

interface WorkbenchTabsProps {
  project: Project;
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  onNameChange?: (name: string) => void;
}

export function WorkbenchTabs({
  project,
  providers,
  styleProfiles,
  onNameChange,
}: WorkbenchTabsProps) {
  // ---- Bible field state ----
  const [fields, setFields] = useState<Record<BibleFieldKey, string>>(() => ({
    inspiration: project.inspiration,
    world_building: project.world_building,
    characters: project.characters,
    outline_master: project.outline_master,
    outline_detail: project.outline_detail,
    story_bible: project.story_bible,
  }));

  // ---- AI generation ----
  const [generatingSection, setGeneratingSection] = useState<BibleFieldKey | null>(null);
  const [generateConfirmSection, setGenerateConfirmSection] = useState<BibleFieldKey | null>(null);
  const generationReaderRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  const handleStopGeneration = useCallback(() => {
    generationReaderRef.current?.cancel();
    generationReaderRef.current = null;
    setGeneratingSection(null);
  }, []);

  const executeGeneration = useCallback(
    async (sectionKey: BibleFieldKey) => {
      if (generatingSection) return;

      // Prerequisite check (non-blocking)
      const prereqs = RECOMMENDED_PREREQUISITES[sectionKey] ?? [];
      const missing = prereqs.filter((k) => !fields[k]?.trim());
      if (missing.length > 0) {
        const labels = missing.map(
          (k) => BIBLE_SECTION_META.find((s) => s.key === k)?.title ?? k,
        );
        toast.info(`建议先填写：${labels.join("、")}，以获得更好的生成效果`);
      }

      setGeneratingSection(sectionKey);

      try {
        const response = await fetch(
          `/api/v1/projects/${project.id}/editor/generate-section`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              section: sectionKey,
              ...fields,
            }),
          },
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || "请求失败");
        }
        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        generationReaderRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = "";
        let generated = "";
        let sseError = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: error")) {
              sseError = true;
            } else if (line.startsWith("data: ")) {
              const dataStr = line.substring(6);
              if (!dataStr) continue;
              if (sseError) {
                const detail = (() => { try { return JSON.parse(dataStr); } catch { return dataStr; } })();
                throw new Error(detail || "生成过程中发生错误");
              }
              try {
                const parsed = JSON.parse(dataStr);
                generated += parsed;
                setFields((prev) => ({ ...prev, [sectionKey]: generated }));
              } catch {
                // ignore parse errors
              }
            }
          }
        }

        // Auto-save after generation
        if (generated) {
          try {
            await api.updateProject(project.id, { [sectionKey]: generated });
          } catch {
            toast.error("自动保存失败");
          }
        }
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "生成失败";
        if (message !== "The operation was cancelled.") {
          toast.error(message);
        }
      } finally {
        generationReaderRef.current = null;
        setGeneratingSection(null);
      }
    },
    [generatingSection, fields, project.id],
  );

  const handleGenerate = useCallback(
    (sectionKey: BibleFieldKey) => {
      if (fields[sectionKey].trim()) {
        setGenerateConfirmSection(sectionKey);
      } else {
        executeGeneration(sectionKey);
      }
    },
    [fields, executeGeneration]
  );

  // Global Escape key listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && generatingSection) {
        handleStopGeneration();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [generatingSection, handleStopGeneration]);

  // ---- Auto-save ----
  const saveTimers = useRef<Record<string, NodeJS.Timeout>>({});

  const debouncedSave = useCallback(
    (field: string, value: string) => {
      if (saveTimers.current[field]) {
        clearTimeout(saveTimers.current[field]);
      }
      saveTimers.current[field] = setTimeout(async () => {
        try {
          await api.updateProject(project.id, { [field]: value });
        } catch {
          toast.error(`保存 ${field} 失败`);
        }
      }, 1000);
    },
    [project.id],
  );

  useEffect(() => {
    const timers = saveTimers.current;
    return () => {
      Object.values(timers).forEach(clearTimeout);
    };
  }, []);

  const handleFieldChange = (key: BibleFieldKey, value: string) => {
    setFields((prev) => ({ ...prev, [key]: value }));
    debouncedSave(key, value);
  };

  // ---- Prerequisite warning builder ----
  const getPrerequisiteWarning = (key: BibleFieldKey): string | null => {
    const prereqs = RECOMMENDED_PREREQUISITES[key] ?? [];
    const missing = prereqs.filter((k) => !fields[k]?.trim());
    if (missing.length === 0) return null;
    const labels = missing.map(
      (k) => BIBLE_SECTION_META.find((s) => s.key === k)?.title ?? k,
    );
    return `💡 建议先完善「${labels.join("」「")}」后再生成${BIBLE_SECTION_META.find((s) => s.key === key)?.title ?? ""}，AI 会参考这些内容来创作。`;
  };

  return (
    <Tabs defaultValue="inspiration" className="w-full">
      <TabsList className="w-full justify-start rounded-none border-b bg-transparent p-0 h-auto">
        {BIBLE_SECTION_META.map((section) => (
          <TabsTrigger
            key={section.key}
            value={section.key}
            className="rounded-none border-b-2 border-transparent px-4 py-3 text-sm data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none"
          >
            {section.title}
          </TabsTrigger>
        ))}
        <TabsTrigger
          value="settings"
          className="ml-auto rounded-none border-b-2 border-transparent px-4 py-3 text-sm text-muted-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none"
        >
          <Settings className="mr-1.5 h-3.5 w-3.5" />
          设置
        </TabsTrigger>
      </TabsList>

      {/* Bible field tabs — forceMount + CSS toggle to preserve state */}
      {BIBLE_SECTION_META.map((section) => (
        <TabsContent
          key={section.key}
          value={section.key}
          forceMount
          className="hidden data-[state=active]:block mt-0 pt-6"
        >
          <div className="max-w-4xl mx-auto">
            <BibleTabContent
              fieldKey={section.key}
              title={section.title}
              value={fields[section.key]}
              onChange={(val) => handleFieldChange(section.key, val)}
              aiEnabled={AI_ENABLED_SECTIONS.has(section.key)}
              prerequisiteWarning={getPrerequisiteWarning(section.key)}
              isGenerating={generatingSection === section.key}
              onGenerate={() => handleGenerate(section.key)}
              onStopGenerate={handleStopGeneration}
            />
          </div>
        </TabsContent>
      ))}

      {/* Settings tab */}
      <TabsContent value="settings" className="mt-0 pt-6">
        <SettingsTab
          project={project}
          providers={providers}
          styleProfiles={styleProfiles}
          onNameChange={onNameChange}
        />
      </TabsContent>

      <AlertDialog
        open={generateConfirmSection !== null}
        onOpenChange={(open) => {
          if (!open) setGenerateConfirmSection(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认覆盖内容？</AlertDialogTitle>
            <AlertDialogDescription>
              当前区块已有内容，AI 生成将覆盖现有内容。该操作不可撤销。是否继续？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (generateConfirmSection) {
                  executeGeneration(generateConfirmSection);
                  setGenerateConfirmSection(null);
                }
              }}
            >
              继续
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Tabs>
  );
}
