import { create } from "zustand";
import type { NarrativeResult } from "@/types/study";
import type { ChatMessage } from "@/types/chat";
import type { ChapterNode } from "@/types/textbook";

interface StudyStore {
  // Active study context
  collectionId: string;
  sectionName: string;
  fileId: string;
  userId: string;

  // Content
  narrative: NarrativeResult | null;
  chatHistory: ChatMessage[];
  language: string;
  forceRegenerate: string;

  // Sidebar
  chapters: ChapterNode[];
  expandedChapters: Set<string>;

  // Streaming
  isStreamingNarrative: boolean;
  streamingText: string;

  // Actions
  setStudyContext: (collectionId: string, sectionName: string, fileId: string) => void;
  setUserId: (userId: string) => void;
  setNarrative: (result: NarrativeResult) => void;
  appendChatMessage: (msg: ChatMessage) => void;
  setChatHistory: (history: ChatMessage[]) => void;
  setLanguage: (lang: string) => void;
  setForceRegenerate: (val: string) => void;
  setChapters: (chapters: ChapterNode[]) => void;
  toggleChapter: (chapterId: string) => void;
  setStreamingNarrative: (streaming: boolean) => void;
  appendStreamToken: (token: string) => void;
  clearStreamingText: () => void;
  reset: () => void;
}

export const useStudyStore = create<StudyStore>((set) => ({
  collectionId: "",
  sectionName: "",
  fileId: "",
  userId: "default",
  narrative: null,
  chatHistory: [],
  language: "en",
  forceRegenerate: "false",
  chapters: [],
  expandedChapters: new Set(),
  isStreamingNarrative: false,
  streamingText: "",

  setStudyContext: (collectionId, sectionName, fileId) =>
    set({ collectionId, sectionName, fileId, narrative: null, chatHistory: [] }),
  setUserId: (userId) => set({ userId }),
  setNarrative: (narrative) => set({ narrative }),
  appendChatMessage: (msg) =>
    set((s) => ({ chatHistory: [...s.chatHistory, msg] })),
  setChatHistory: (history) => set({ chatHistory: history }),
  setLanguage: (language) => set({ language }),
  setForceRegenerate: (forceRegenerate) => set({ forceRegenerate }),
  setChapters: (chapters) => set({ chapters }),
  toggleChapter: (chapterId) =>
    set((s) => {
      const next = new Set(s.expandedChapters);
      if (next.has(chapterId)) next.delete(chapterId);
      else next.add(chapterId);
      return { expandedChapters: next };
    }),
  setStreamingNarrative: (isStreamingNarrative) => set({ isStreamingNarrative }),
  appendStreamToken: (token) => set((s) => ({ streamingText: s.streamingText + token })),
  clearStreamingText: () => set({ streamingText: "" }),
  reset: () =>
    set({
      collectionId: "",
      sectionName: "",
      fileId: "",
      narrative: null,
      chatHistory: [],
      streamingText: "",
      isStreamingNarrative: false,
    }),
}));
