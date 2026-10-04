import { create } from "zustand";
import { persist } from "zustand/middleware";

export type StudyTab = "game" | "diagram" | "pdf";

interface UIStore {
  sidebarOpen: boolean;
  ttsEnabled: boolean;
  language: string;
  activeTab: StudyTab;

  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTtsEnabled: (enabled: boolean) => void;
  setLanguage: (lang: string) => void;
  setActiveTab: (tab: StudyTab) => void;
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      ttsEnabled: false,
      language: "en",
      activeTab: "diagram",

      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setTtsEnabled: (ttsEnabled) => set({ ttsEnabled }),
      setLanguage: (language) => set({ language }),
      setActiveTab: (activeTab) => set({ activeTab }),
    }),
    {
      name: "learnai-ui",
      // activeTab is per-visit UI state; don't restore stale values across sessions
      partialize: ({ sidebarOpen, ttsEnabled, language }) => ({ sidebarOpen, ttsEnabled, language }),
    }
  )
);
