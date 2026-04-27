import { createStore } from "zustand";
import type { ProjectChapter } from "@/lib/types";

type ChapterSelection = { volumeIndex: number; chapterIndex: number };

export type EditorState = {
  currentChapter: ChapterSelection | null;
  setCurrentChapter: (selection: ChapterSelection | null | ((prev: ChapterSelection | null) => ChapterSelection | null)) => void;
  
  selectedVolumeIndex: number | null;
  setSelectedVolumeIndex: (index: number | null | ((prev: number | null) => number | null)) => void;
  
  chapterFocusMode: "idle" | "navigate" | "generate_beats";
  setChapterFocusMode: (mode: "idle" | "navigate" | "generate_beats" | ((prev: "idle" | "navigate" | "generate_beats") => "idle" | "navigate" | "generate_beats")) => void;
  
  content: string;
  setContent: (content: string | ((prev: string) => string)) => void;
  
  savedChapterContent: string;
  setSavedChapterContent: (content: string | ((prev: string) => string)) => void;
  
  isLeftExpanded: boolean;
  setIsLeftExpanded: (expanded: boolean | ((prev: boolean) => boolean)) => void;
  
  isRightExpanded: boolean;
  setIsRightExpanded: (expanded: boolean | ((prev: boolean) => boolean)) => void;
  
  leftPanelMode: "navigation" | "settings";
  setLeftPanelMode: (mode: "navigation" | "settings" | ((prev: "navigation" | "settings") => "navigation" | "settings")) => void;
};

export const createEditorStore = () => createStore<EditorState>((set) => ({
  currentChapter: null,
  setCurrentChapter: (updater) => set((state) => ({ 
    currentChapter: typeof updater === 'function' ? updater(state.currentChapter) : updater 
  })),

  selectedVolumeIndex: null,
  setSelectedVolumeIndex: (updater) => set((state) => ({ 
    selectedVolumeIndex: typeof updater === 'function' ? updater(state.selectedVolumeIndex) : updater 
  })),

  chapterFocusMode: "idle",
  setChapterFocusMode: (updater) => set((state) => ({ 
    chapterFocusMode: typeof updater === 'function' ? updater(state.chapterFocusMode) : updater 
  })),

  content: "",
  setContent: (updater) => set((state) => ({ 
    content: typeof updater === 'function' ? updater(state.content) : updater 
  })),

  savedChapterContent: "",
  setSavedChapterContent: (updater) => set((state) => ({ 
    savedChapterContent: typeof updater === 'function' ? updater(state.savedChapterContent) : updater 
  })),

  isLeftExpanded: false,
  setIsLeftExpanded: (updater) => set((state) => ({ 
    isLeftExpanded: typeof updater === 'function' ? updater(state.isLeftExpanded) : updater 
  })),

  isRightExpanded: false,
  setIsRightExpanded: (updater) => set((state) => ({ 
    isRightExpanded: typeof updater === 'function' ? updater(state.isRightExpanded) : updater 
  })),

  leftPanelMode: "navigation",
  setLeftPanelMode: (updater) => set((state) => ({ 
    leftPanelMode: typeof updater === 'function' ? updater(state.leftPanelMode) : updater 
  })),
}));
