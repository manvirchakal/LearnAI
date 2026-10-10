import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIStore {
  sidebarOpen: boolean;
  ttsEnabled: boolean;
  language: string;
  /** Contents sheet on small screens (the desktop rail uses sidebarOpen) */
  tocSheetOpen: boolean;

  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTtsEnabled: (enabled: boolean) => void;
  setLanguage: (lang: string) => void;
  setTocSheetOpen: (open: boolean) => void;
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      ttsEnabled: false,
      language: "en",
      tocSheetOpen: false,

      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setTtsEnabled: (ttsEnabled) => set({ ttsEnabled }),
      setLanguage: (language) => set({ language }),
      setTocSheetOpen: (tocSheetOpen) => set({ tocSheetOpen }),
    }),
    {
      name: "learnai-ui",
      partialize: ({ sidebarOpen, ttsEnabled, language }) => ({ sidebarOpen, ttsEnabled, language }),
    }
  )
);
