"use client";
import { Box } from "@mui/material";
import { ReactNode } from "react";
import TopNav from "./TopNav";
import Sidebar, { DRAWER_WIDTH } from "./Sidebar";
import { useUIStore } from "@/store/uiStore";
import type { BookDetail } from "@/types/book";

interface Props {
  children: ReactNode;
  /** When set, shows the book's table of contents in a sidebar */
  book?: BookDetail;
  activeSectionId?: string;
}

export default function AppShell({ children, book, activeSectionId }: Props) {
  const { sidebarOpen } = useUIStore();
  const withSidebar = !!book && sidebarOpen;

  return (
    <Box sx={{ display: "flex" }}>
      <TopNav showMenuButton={!!book} />
      {book && <Sidebar book={book} activeSectionId={activeSectionId} />}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          minWidth: 0,
          mt: "64px",
          ml: withSidebar ? 0 : book ? `-${DRAWER_WIDTH}px` : 0,
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
