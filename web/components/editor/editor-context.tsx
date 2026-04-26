"use client";

import React, { createContext, useContext, useRef, ReactNode } from "react";
import { useStore } from "zustand";
import type { Project } from "@/lib/types";
import { createEditorStore, type EditorState } from "./editor-store";

type ChapterSelection = { volumeIndex: number; chapterIndex: number };

type EditorContextType = {
  project: Project;
  store: ReturnType<typeof createEditorStore>;
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
  const storeRef = useRef<ReturnType<typeof createEditorStore>>(null);
  
  if (!storeRef.current) {
    const store = createEditorStore();
    store.setState({
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
    storeRef.current = store;
  }

  return (
    <EditorContext.Provider value={{ project, store: storeRef.current }}>
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

export function useEditorStore<T>(selector: (state: EditorState) => T): T {
  const { store } = useEditorContext();
  return useStore(store, selector);
}

