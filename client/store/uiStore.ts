import { create } from "zustand";
import { persist } from "zustand/middleware";

export type StudyTab = "chat" | "game" | "diagram" | "pdf";

interface UIStore {
  sidebarOpen: boolean;
  ttsEnabled: boolean;
  language: string;
  activeTab: StudyTab;
  /** Contents sheet on small screens (the desktop rail uses sidebarOpen) */
  tocSheetOpen: boolean;

  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTtsEnabled: (enabled: boolean) => void;
  setLanguage: (lang: string) => void;
  setActiveTab: (tab: StudyTab) => void;
  setTocSheetOpen: (open: boolean) => void;
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      ttsEnabled: false,
      language: "en",
      activeTab: "chat",
      tocSheetOpen: false,

      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setTtsEnabled: (ttsEnabled) => set({ ttsEnabled }),
      setLanguage: (language) => set({ language }),
      setActiveTab: (activeTab) => set({ activeTab }),
      setTocSheetOpen: (tocSheetOpen) => set({ tocSheetOpen }),
    }),
    {
      name: "learnai-ui",
      // activeTab is per-visit UI state; don't restore stale values across sessions
      partialize: ({ sidebarOpen, ttsEnabled, language }) => ({ sidebarOpen, ttsEnabled, language }),
    }
  )
);
