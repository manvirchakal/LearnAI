"use client";
import {
  Drawer, List, ListItemButton, ListItemText, Collapse,
  Typography, Box, Divider, IconButton,
} from "@mui/material";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import { useStudyStore } from "@/store/studyStore";
import { useUIStore } from "@/store/uiStore";
import type { ChapterNode } from "@/types/textbook";
import { useRouter } from "next/navigation";

const DRAWER_WIDTH = 280;

interface Props {
  chapters: ChapterNode[];
  collectionIdMap?: Record<string, string>; // sectionTitle → collectionId
  fileId?: string;
}

export default function Sidebar({ chapters, collectionIdMap = {}, fileId = "" }: Props) {
  const { sidebarOpen } = useUIStore();
  const { expandedChapters, toggleChapter, setStudyContext } = useStudyStore();
  const router = useRouter();

  const handleSectionClick = (sectionId: string, sectionTitle: string) => {
    const collectionId = collectionIdMap[sectionTitle] || sectionId;
    setStudyContext(collectionId, sectionTitle, fileId);
    router.push(`/study/${collectionId}/${encodeURIComponent(sectionTitle)}`);
  };

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
        <Typography variant="subtitle2" color="text.secondary" sx={{ fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
          Contents
        </Typography>
      </Box>
      <Divider />
      <List dense disablePadding>
        {chapters.map((chapter) => (
          <Box key={chapter.id}>
            <ListItemButton onClick={() => toggleChapter(chapter.id)} sx={{ py: 1 }}>
              <ListItemText
                primary={chapter.title}
                primaryTypographyProps={{ variant: "body2", fontWeight: 600, fontSize: 13 }}
              />
              {expandedChapters.has(chapter.id) ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
            </ListItemButton>
            <Collapse in={expandedChapters.has(chapter.id)}>
              <List dense disablePadding>
                {chapter.sections.map((section) => (
                  <ListItemButton
                    key={section.id}
                    sx={{ pl: 4, py: 0.5 }}
                    onClick={() => handleSectionClick(section.id, section.title)}
                  >
                    <ListItemText
                      primary={section.title}
                      primaryTypographyProps={{ variant: "caption", color: "text.secondary" }}
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
