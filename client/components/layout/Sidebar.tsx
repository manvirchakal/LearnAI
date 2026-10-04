"use client";
import { Box, Collapse, Divider, Drawer, List, ListItemButton, ListItemText, Typography } from "@mui/material";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import Link from "next/link";
import { useState } from "react";
import { useUIStore } from "@/store/uiStore";
import type { BookDetail } from "@/types/book";

export const DRAWER_WIDTH = 280;

interface Props {
  book: BookDetail;
  activeSectionId?: string;
}

export default function Sidebar({ book, activeSectionId }: Props) {
  const { sidebarOpen } = useUIStore();
  const activeChapter = book.chapters.find((c) => c.sections.some((s) => s.id === activeSectionId))?.id;
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(activeChapter ? [activeChapter] : []));

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <Drawer
      variant="persistent"
      open={sidebarOpen}
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          boxSizing: "border-box",
          top: 64,
          height: "calc(100% - 64px)",
          borderRight: "1px solid #e9ecef",
        },
      }}
    >
      <Box sx={{ p: 2 }}>
        <Link href={`/study/${book.file_id}`} style={{ textDecoration: "none", color: "inherit" }}>
          <Typography variant="subtitle2" fontWeight={700} noWrap title={book.title}>
            {book.title}
          </Typography>
        </Link>
        <Typography variant="caption" color="text.secondary">
          {book.section_count} sections · {book.num_pages} pages
        </Typography>
      </Box>
      <Divider />
      <List dense disablePadding>
        {book.chapters.map((chapter) => (
          <Box key={chapter.id}>
            <ListItemButton onClick={() => toggle(chapter.id)} sx={{ py: 1 }}>
              <ListItemText
                primary={chapter.title}
                secondary={chapter.number}
                primaryTypographyProps={{ variant: "body2", fontWeight: 600, fontSize: 13 }}
                secondaryTypographyProps={{ fontSize: 11 }}
              />
              {expanded.has(chapter.id) ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
            </ListItemButton>
            <Collapse in={expanded.has(chapter.id)}>
              <List dense disablePadding>
                {chapter.sections.map((section) => (
                  <ListItemButton
                    key={section.id}
                    component={Link}
                    href={`/study/${book.file_id}/${section.id}`}
                    selected={section.id === activeSectionId}
                    sx={{ pl: 4, py: 0.5 }}
                  >
                    <ListItemText
                      primary={section.title}
                      secondary={`pp. ${section.start_page}–${section.end_page}`}
                      primaryTypographyProps={{ variant: "caption", fontWeight: section.id === activeSectionId ? 600 : 400 }}
                      secondaryTypographyProps={{ fontSize: 10 }}
                    />
                  </ListItemButton>
                ))}
              </List>
            </Collapse>
          </Box>
        ))}
      </List>
    </Drawer>
  );
}
