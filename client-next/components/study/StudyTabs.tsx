"use client";
import SportsEsportsIcon from "@mui/icons-material/SportsEsports";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import Tabs from "@/components/ui/Tabs";
import { useUIStore } from "@/store/uiStore";

const TABS = [
  { value: "game", label: "Game", icon: <SportsEsportsIcon fontSize="small" /> },
  { value: "diagram", label: "Diagrams", icon: <AccountTreeIcon fontSize="small" /> },
  { value: "pdf", label: "PDF", icon: <PictureAsPdfIcon fontSize="small" /> },
];

export default function StudyTabs() {
  const { activeTab, setActiveTab } = useUIStore();
  return <Tabs items={TABS} value={activeTab} onChange={setActiveTab} />;
}
