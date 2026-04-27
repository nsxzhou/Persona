"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Settings } from "lucide-react";
import { toast } from "sonner";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BibleTabContent } from "@/components/bible-tab-content";
import { OutlineDetailTab } from "@/components/outline-detail-tab";
import { RegenerateDialog } from "@/components/regenerate-dialog";
import { SettingsTab } from "@/components/settings-tab";
import { api } from "@/lib/api";
import type { RegenerateOptions } from "@/lib/api-client";
import { consumeTextEventStream } from "@/lib/sse";
import {
  AI_ENABLED_SECTIONS,
  BIBLE_SECTION_META,
  RECOMMENDED_PREREQUISITES,
  type BibleFieldKey,
} from "@/lib/bible-fields";
import type {
  PlotProfileListItem,
  Project,
  ProjectBible,
  ProjectChapter,
  ProviderConfig,
  StyleProfileListItem,
} from "@/lib/types";

interface WorkbenchTabsProps {
  project: Project;
  projectBible: ProjectBible;
  providers: ProviderConfig[];
  styleProfiles: StyleProfileListItem[];
  plotProfiles: PlotProfileListItem[];
  onNameChange?: (name: string) => void;
  activeTab?: string;
  onActiveTabChange?: (value: string) => void;
  highlightedVolumeIndex?: number | null;
}

export function WorkbenchTabs({
  project,
  projectBible,
  providers,
  styleProfiles,
  plotProfiles,
  onNameChange,
  activeTab = "description",
  onActiveTabChange,
  highlightedVolumeIndex = null,
}: WorkbenchTabsProps) {
  // ---- Bible field state ----

  const [fields, setFields] = useState<Record<BibleFieldKey, string>>(() => ({
    description: project.description,
    world_building: projectBible.world_building,
    characters_blueprint: projectBible.characters_blueprint,
    outline_master: projectBible.outline_master,
    outline_detail: projectBible.outline_detail,
    characters_status: projectBible.characters_status,
    runtime_state: projectBible.runtime_state,
    runtime_threads: projectBible.runtime_threads,
  }));

  // ---- AI generation ----
  const [generatingSection, setGeneratingSection] = useState<BibleFieldKey | null>(null);
  const [regenerateSection, setRegenerateSection] = useState<BibleFieldKey | null>(null);
  const [chapters, setChapters] = useState<ProjectChapter[]>([]);
  const [chaptersLoadError, setChaptersLoadError] = useState<string | null>(null);
  const generationReaderRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getProjectChapters(project.id)
      .then((loaded) => {
        if (!cancelled) {
          setChaptersLoadError(null);
          setChapters(loaded);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setChaptersLoadError(e instanceof Error ? e.message : "加载章节失败");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [project.id]);

  const handleRetryChapters = useCallback(async () => {
    try {
      const loaded = await api.getProjectChapters(project.id);
      setChaptersLoadError(null);
      setChapters(loaded);
    } catch (e: unknown) {
      setChaptersLoadError(e instanceof Error ? e.message : "加载章节失败");
    }
  }, [project.id]);

  const handleStopGeneration = useCallback(() => {
    generationReaderRef.current?.cancel();
    generationReaderRef.current = null;
    setGeneratingSection(null);
  }, []);

  const executeGeneration = useCallback(
    async (sectionKey: BibleFieldKey, options?: RegenerateOptions) => {
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
        const response = await api.generateSection(
          project.id,
          {
            section: sectionKey,
            ...fields,
          },
          options,
        );

        if (!response.body) throw new Error("No response body");

        const reader = response.body.getReader();
        generationReaderRef.current = reader;
        let generated = "";
        await consumeTextEventStream(reader, {
          onData: (_chunk, fullText) => {
            generated = fullText;
            setFields((prev) => ({ ...prev, [sectionKey]: fullText }));
          },
        });

        // Auto-save after generation
        if (generated) {
          try {
            if (sectionKey === "description") {
              await api.updateProject(project.id, { [sectionKey]: generated });
            } else {
              await api.updateProjectBible(project.id, { [sectionKey]: generated });
            }
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
        setRegenerateSection(sectionKey);
      } else {
        executeGeneration(sectionKey);
      }
    },
    [fields, executeGeneration]
  );

  const handleRegenerateConfirm = useCallback(
    (feedback: string) => {
      const section = regenerateSection;
      if (!section) return;
      setRegenerateSection(null);
      executeGeneration(section, {
        previousOutput: fields[section] || undefined,
        userFeedback: feedback || undefined,
      });
    },
    [regenerateSection, fields, executeGeneration],
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
          if (field === "description") {
            await api.updateProject(project.id, { [field]: value });
          } else {
            await api.updateProjectBible(project.id, { [field]: value });
          }
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
    <div className="w-full">
      {chaptersLoadError ? (
        <div className="mb-4 flex items-center gap-3 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <span>{chaptersLoadError}</span>
          <button
            type="button"
            className="underline underline-offset-4"
            onClick={() => void handleRetryChapters()}
          >
            重试加载章节
          </button>
        </div>
      ) : null}
      <Tabs value={activeTab} onValueChange={onActiveTabChange} className="w-full">
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
            {section.key === "outline_detail" ? (
              <OutlineDetailTab
                value={fields.outline_detail}
                onChange={(val) => handleFieldChange("outline_detail", val)}
                projectId={project.id}
                outlineMaster={fields.outline_master}
                chapters={chapters}
                highlightedVolumeIndex={highlightedVolumeIndex}
              />
            ) : (
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
            )}
          </div>
        </TabsContent>
      ))}

      {/* Settings tab */}
        <TabsContent value="settings" className="mt-0 pt-6">
          <SettingsTab
            project={project}
            providers={providers}
            styleProfiles={styleProfiles}
            plotProfiles={plotProfiles}
            onNameChange={onNameChange}
          />
        </TabsContent>

        <RegenerateDialog
          open={regenerateSection !== null}
          title={
            regenerateSection
              ? `重新生成「${
                  BIBLE_SECTION_META.find((s) => s.key === regenerateSection)?.title ?? regenerateSection
                }」`
              : ""
          }
          description="当前已有内容，将在其基础上按你的意见重新生成。意见可填可不填。"
          busy={generatingSection !== null}
          onCancel={() => setRegenerateSection(null)}
          onConfirm={handleRegenerateConfirm}
        />
      </Tabs>
    </div>
  );
}
