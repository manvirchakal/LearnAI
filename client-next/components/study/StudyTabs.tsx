"use client";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import ForumIcon from "@mui/icons-material/Forum";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import SportsEsportsIcon from "@mui/icons-material/SportsEsports";
import Tabs from "@/components/ui/Tabs";
import { useUIStore, type StudyTab } from "@/store/uiStore";

const TABS = [
  { value: "chat", label: "Chat", icon: <ForumIcon fontSize="small" /> },
  { value: "game", label: "Game", icon: <SportsEsportsIcon fontSize="small" /> },
  { value: "diagram", label: "Diagrams", icon: <AccountTreeIcon fontSize="small" /> },
  { value: "pdf", label: "PDF", icon: <PictureAsPdfIcon fontSize="small" /> },
];

export default function StudyTabs() {
  const { activeTab, setActiveTab } = useUIStore();
  return <Tabs items={TABS} value={activeTab} onChange={(v) => setActiveTab(v as StudyTab)} variant="fullWidth" />;
}
