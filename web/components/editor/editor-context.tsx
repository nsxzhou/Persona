"use client";

import React, { createContext, useContext, useState, useRef, ReactNode } from "react";
import type { Project, ProjectChapter } from "@/lib/types";

type ChapterSelection = { volumeIndex: number; chapterIndex: number };

type EditorContextType = {
  project: Project;
  chapters: ProjectChapter[];
  setChapters: React.Dispatch<React.SetStateAction<ProjectChapter[]>>;
  isLoadingChapters: boolean;
  setIsLoadingChapters: React.Dispatch<React.SetStateAction<boolean>>;
  currentChapter: ChapterSelection | null;
  setCurrentChapter: React.Dispatch<React.SetStateAction<ChapterSelection | null>>;
  selectedVolumeIndex: number | null;
  setSelectedVolumeIndex: React.Dispatch<React.SetStateAction<number | null>>;
  chapterFocusMode: "idle" | "navigate" | "generate_beats";
  setChapterFocusMode: React.Dispatch<React.SetStateAction<"idle" | "navigate" | "generate_beats">>;
  content: string;
  setContent: React.Dispatch<React.SetStateAction<string>>;
  savedChapterContent: string;
  setSavedChapterContent: React.Dispatch<React.SetStateAction<string>>;
  isLeftExpanded: boolean;
  setIsLeftExpanded: React.Dispatch<React.SetStateAction<boolean>>;
  isRightExpanded: boolean;
  setIsRightExpanded: React.Dispatch<React.SetStateAction<boolean>>;
  leftPanelMode: "navigation" | "settings";
  setLeftPanelMode: React.Dispatch<React.SetStateAction<"navigation" | "settings">>;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
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
  const [chapters, setChapters] = useState<ProjectChapter[]>([]);
  const [isLoadingChapters, setIsLoadingChapters] = useState(true);
  const [currentChapter, setCurrentChapter] = useState<ChapterSelection | null>(initialChapterSelection);
  const [selectedVolumeIndex, setSelectedVolumeIndex] = useState<number | null>(initialChapterSelection?.volumeIndex ?? null);
  const [chapterFocusMode, setChapterFocusMode] = useState<"idle" | "navigate" | "generate_beats">(initialChapterSelection ? (initialIntent ?? "navigate") : "idle");

  const [content, setContent] = useState("");
  const [savedChapterContent, setSavedChapterContent] = useState("");
  
  const [isLeftExpanded, setIsLeftExpanded] = useState(Boolean(initialChapterSelection));
  const [isRightExpanded, setIsRightExpanded] = useState(initialIntent === "generate_beats");
  const [leftPanelMode, setLeftPanelMode] = useState<"navigation" | "settings">("navigation");

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  return (
    <EditorContext.Provider
      value={{
        project,
        chapters,
        setChapters,
        isLoadingChapters,
        setIsLoadingChapters,
        currentChapter,
        setCurrentChapter,
        selectedVolumeIndex,
        setSelectedVolumeIndex,
        chapterFocusMode,
        setChapterFocusMode,
        content,
        setContent,
        savedChapterContent,
        setSavedChapterContent,
        isLeftExpanded,
        setIsLeftExpanded,
        isRightExpanded,
        setIsRightExpanded,
        leftPanelMode,
        setLeftPanelMode,
        textareaRef,
      }}
    >
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
