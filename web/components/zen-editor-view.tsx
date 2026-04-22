"use client";

import type { Project, ProjectBible } from "@/lib/types";
import { EditorProvider } from "@/components/editor/editor-context";
import { EditorContentArea } from "@/components/editor/editor-content-area";

type ChapterSelection = { volumeIndex: number; chapterIndex: number };

export function ZenEditorView({
  project: initialProject,
  projectBible: initialProjectBible,
  activeProfileName,
  initialChapterSelection = null,
  initialIntent = null,
}: {
  project: Project;
  projectBible: ProjectBible;
  activeProfileName?: string;
  initialChapterSelection?: ChapterSelection | null;
  initialIntent?: "navigate" | "generate_beats" | null;
}) {
  return (
    <EditorProvider 
      project={initialProject} 
      initialChapterSelection={initialChapterSelection}
      initialIntent={initialIntent}
    >
      <EditorContentArea 
        activeProfileName={activeProfileName} 
        initialProjectBible={initialProjectBible}
      />
    </EditorProvider>
  );
}
