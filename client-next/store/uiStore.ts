import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIStore {
  sidebarOpen: boolean;
  ttsEnabled: boolean;
  language: string;
  activeTab: "narrative" | "game" | "diagram" | "pdf";

  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTtsEnabled: (enabled: boolean) => void;
  setLanguage: (lang: string) => void;
  setActiveTab: (tab: UIStore["activeTab"]) => void;
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      ttsEnabled: false,
      language: "en",
      activeTab: "narrative",

      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setTtsEnabled: (ttsEnabled) => set({ ttsEnabled }),
      setLanguage: (language) => set({ language }),
      setActiveTab: (activeTab) => set({ activeTab }),
    }),
    { name: "learnai-ui" }
  )
);
