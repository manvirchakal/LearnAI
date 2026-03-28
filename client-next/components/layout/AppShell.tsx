"use client";
import { Box } from "@mui/material";
import { ReactNode } from "react";
import TopNav from "./TopNav";
import Sidebar from "./Sidebar";
import { useUIStore } from "@/store/uiStore";
import type { ChapterNode } from "@/types/textbook";

const DRAWER_WIDTH = 280;

interface Props {
  children: ReactNode;
  chapters?: ChapterNode[];
  collectionIdMap?: Record<string, string>;
  fileId?: string;
}

export default function AppShell({ children, chapters = [], collectionIdMap, fileId }: Props) {
  const { sidebarOpen } = useUIStore();

  return (
    <Box sx={{ display: "flex" }}>
      <TopNav />
      {chapters.length > 0 && (
        <Sidebar chapters={chapters} collectionIdMap={collectionIdMap} fileId={fileId} />
      )}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          mt: "64px",
          ml: chapters.length > 0 && sidebarOpen ? `${DRAWER_WIDTH}px` : 0,
          transition: "margin 225ms cubic-bezier(0.0, 0, 0.2, 1) 0ms",
          minHeight: "calc(100vh - 64px)",
          bgcolor: "#f8f9fa",
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
