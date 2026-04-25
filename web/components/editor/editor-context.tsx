"use client";

import React, { createContext, useContext, useEffect, ReactNode } from "react";
import type { Project } from "@/lib/types";
import { useEditorStore } from "./editor-store";

type ChapterSelection = { volumeIndex: number; chapterIndex: number };

type EditorContextType = {
  project: Project;
};

const EditorContext = createContext<EditorContextType | null>(null);

export function EditorProvider({
  children,
  project,
  initialChapterSelection = null,
  initialIntent = null,
}: {
  children: ReactNode;
  project: Project;
  initialChapterSelection?: ChapterSelection | null;
  initialIntent?: "navigate" | "generate_beats" | null;
}) {
  useEffect(() => {
    // Initialize the store
    useEditorStore.setState({
      chapters: [],
      isLoadingChapters: true,
      currentChapter: initialChapterSelection,
      selectedVolumeIndex: initialChapterSelection?.volumeIndex ?? null,
      chapterFocusMode: initialChapterSelection ? (initialIntent ?? "navigate") : "idle",
      content: "",
      savedChapterContent: "",
      isLeftExpanded: Boolean(initialChapterSelection),
      isRightExpanded: initialIntent === "generate_beats",
      leftPanelMode: "navigation",
    });
  }, [initialChapterSelection, initialIntent]);

  return (
    <EditorContext.Provider value={{ project }}>
      {children}
    </EditorContext.Provider>
  );
}

export function useEditorContext() {
  const context = useContext(EditorContext);
  if (!context) {
    throw new Error("useEditorContext must be used within an EditorProvider");
  }
  return context;
}

